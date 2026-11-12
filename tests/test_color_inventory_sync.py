"""The colour inventory is generated, so it can drift; these keep it honest.

Nothing ran ``tools/color_audit.py`` between 18dbe02 and 2026-11-11, by which
point ``docs/ui_color_inventory.md`` was 3,250 lines stale and still asserted a
retired colour rule. The determinism tests come first because the staleness
test is built on them: four report sections came out in thread order.

Spec:  no spec file -- four criteria, no user-visible behaviour (CLAUDE.md,
       *Records are filed, not tested*).
Tests: this file.
"""

from __future__ import annotations

import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import color_audit  # noqa: E402  (needs the path above)


# A hand-built stand-in for a scan, shaped to hit every ordering decision
# build_report makes: `#aabbcc`/`#ddeeff` tie at two hex occurrences, "red"/
# "blue" tie at two named, and app_settings and tuples carry three lines each
# out of path order. A tie is the only place insertion order can leak out.
SCAN_FIXTURE = {
    "hex": [
        "src/b.py:10:    fg_color=\"#aabbcc\"",
        "src/a.py:20:    fg_color=\"#ddeeff\"",
        "src/c.py:5:     border_color=\"#aabbcc\"",
        "src/a.py:3:     text_color=\"#ddeeff\"",
    ],
    "named": [
        "src/b.py:11:    text_color=\"red\"",
        "src/a.py:21:    text_color=\"blue\"",
        "src/c.py:6:     hover_color=\"red\"",
        "src/a.py:4:     fg_color=\"blue\"",
    ],
    # Non-overlapping with `hex`/`named` on purpose: CIV-M5 proves the scans
    # disjoint against real rg, so an overlapping fixture would assert the bug.
    "theme_files": [
        'themes/t.json:2:      "#abcdef",',
        'themes/t.json:9:      "teal",',
    ],
    "widget": [
        "src/b.py:10:    fg_color=\"#aabbcc\"",
        "src/a.py:20:    hover_color=\"#ddeeff\"",
    ],
    "theme_api": [
        "src/z.py:9:     set_appearance_mode(\"dark\")",
        "src/a.py:1:     set_default_color_theme(\"blue\")",
    ],
    "tuples": [
        "src/z.py:40:    fg_color=(\"white\", \"black\")",
        "src/a.py:2:     text_color=(\"black\", \"white\")",
        "src/m.py:7:     border_color=(\"gray\", \"grey\")",
    ],
    "app_settings": [
        "src/settings.py:80:  self.theme_name = value",
        "src/settings.py:9:   self.appearance_mode = value",
        "src/settings.py:12:  self.drag_schedule_date_text_color = value",
    ],
}


def test_civm11_the_fixture_covers_every_scan_the_generator_runs():
    """A key missing here would exercise a report the generator never builds."""
    assert set(SCAN_FIXTURE) == set(color_audit.SCAN_COMMANDS), (
        "SCAN_FIXTURE and SCAN_COMMANDS disagree: "
        f"only in fixture {sorted(set(SCAN_FIXTURE) - set(color_audit.SCAN_COMMANDS))}, "
        f"only in generator {sorted(set(color_audit.SCAN_COMMANDS) - set(SCAN_FIXTURE))}"
    )


def _shuffled(scans: dict[str, list[str]], seed: int) -> dict[str, list[str]]:
    rnd = random.Random(seed)
    out = {}
    for name, lines in scans.items():
        copy = list(lines)
        rnd.shuffle(copy)
        out[name] = copy
    return out


# --------------------------------------------------------------------------
# CIV-M1 — the generator is deterministic
# --------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 2, 7, 13])
def test_civm11_the_report_does_not_depend_on_scan_order(seed):
    """Same matches in a different order must give the same document.

    ripgrep searches in parallel and does not promise an order, so this is the
    property that makes a regenerate-and-compare gate possible at all.
    """
    base = color_audit.build_report(SCAN_FIXTURE)
    reordered = color_audit.build_report(_shuffled(SCAN_FIXTURE, seed))
    assert reordered == base, (
        f"build_report is order-dependent (seed {seed}). Some section emits "
        "scan results in arrival order; sort it by (path, line), and break "
        "frequency-table ties by colour name."
    )


def test_civm11_the_fixture_actually_contains_the_ties_that_catch_this():
    """Adversarial: a fixture with no tied counts would pass against the bug."""
    from collections import Counter

    hex_counts = Counter()
    for line in SCAN_FIXTURE["hex"]:
        hex_counts.update(c.lower() for c in color_audit.HEX_RE.findall(line))
    named_counts = Counter()
    for line in SCAN_FIXTURE["named"]:
        named_counts.update(m.group("c").lower() for m in color_audit.NAMED_RE.finditer(line))

    assert sorted(hex_counts.values()) == [2, 2], (
        f"the hex fixture no longer ties: {dict(hex_counts)}"
    )
    assert sorted(named_counts.values()) == [2, 2], (
        f"the named fixture no longer ties: {dict(named_counts)}"
    )


def test_civm12_every_scan_command_asks_ripgrep_to_sort():
    """Belt and braces at the source, and the document claims it.

    The report's own header says "deterministic `rg` scans". Downstream sorting
    is what the gate relies on, but an unsorted scan makes that claim false and
    leaves any section added later order-dependent by default.
    """
    unsorted_scans = [
        name for name, cmd in color_audit.SCAN_COMMANDS.items()
        if "--sort" not in cmd
    ]
    assert unsorted_scans == [], (
        f"these scans do not pass --sort to rg: {unsorted_scans}. "
        "ripgrep's default output order depends on thread scheduling."
    )


def test_civm12_every_scan_command_asks_ripgrep_for_the_filename():
    """A scan given one explicit file omits the path, and then nothing parses.

    rg prints the filename only when searching more than one file, so
    `app_settings` came back as `55:    appearance_mode: str = "dark"`:
    parse_line returned None for all 26 lines and the block came out in
    lexical order, 445, 446, 447, 55, 56, 626. rg 14.1.1, 2026-11-11.
    """
    without_filename = [
        name for name, cmd in color_audit.SCAN_COMMANDS.items()
        if "-H" not in cmd and "--with-filename" not in cmd
    ]
    assert without_filename == [], (
        f"these scans do not ask rg for the filename: {without_filename}. "
        "Given one explicit file rg emits 'line:text', and every line of "
        "that scan fails parse_line while the report still builds."
    )


# --------------------------------------------------------------------------
# CIV-M2 — a stale inventory fails the suite
# --------------------------------------------------------------------------

def test_civm2_the_committed_inventory_matches_a_fresh_generation():
    """The gate. Regenerate after any change that adds or removes a colour."""
    committed = color_audit.DEFAULT_OUTPUT
    assert committed.exists(), f"{committed} is missing"

    fresh = color_audit.build_report(color_audit.scan_all())
    on_disk = committed.read_text(encoding="utf-8")

    if fresh != on_disk:
        fresh_lines = fresh.splitlines()
        disk_lines = on_disk.splitlines()
        first = next(
            (i for i, (a, b) in enumerate(zip(disk_lines, fresh_lines)) if a != b),
            min(len(disk_lines), len(fresh_lines)),
        )
        pytest.fail(
            f"docs/ui_color_inventory.md is stale ({len(disk_lines)} lines on "
            f"disk, {len(fresh_lines)} regenerated; first difference at line "
            f"{first + 1}). Run:\n"
            "    ./venv/bin/python tools/color_audit.py\n"
            "and commit the result. It is generated -- do not edit it by hand.\n"
            "Note the scan reads the WORKING TREE, not HEAD: uncommitted or "
            "untracked files of your own, or another session's, are included, "
            "so regenerate only once the tree holds what you mean to commit.\n"
            "If this fails only on CI, compare `rg --version` there with "
            "yours: the report is a byte comparison against the output of an "
            "unpinned third-party binary, and rg has changed observable "
            "behaviour between releases."
        )


def test_civm5_the_scans_feeding_one_count_do_not_overlap():
    """Two scans over the same bytes counted every theme colour twice.

    When all three searched from the repo root, `theme_files` re-counted what
    `hex` and `named` had. Measured 2026-11-11 before the fix: the table read
    `#000000` 79 against 57 rows in the occurrence table, which dedups by full
    identity. Disjointness now holds by construction, and that construction is
    what this asserts -- not those figures, nor the glob that used to carry it.
    """
    def keys(scan_name):
        out = set()
        for line in color_audit.run_rg(color_audit.SCAN_COMMANDS[scan_name]):
            entry = color_audit.parse_line(line)
            if entry:
                out.add((entry.path, entry.line))
        return out

    theme_files = keys("theme_files")
    for counted_with in ("hex", "named"):
        overlap = keys(counted_with) & theme_files
        assert overlap == set(), (
            f"the {counted_with!r} and 'theme_files' scans both feed one "
            f"frequency table and cover {len(overlap)} of the same file-lines, "
            f"so every match there is counted twice. Example: {sorted(overlap)[:3]}"
        )


# --------------------------------------------------------------------------
# CIV-M13 — the report's content, not just its stability
# --------------------------------------------------------------------------

def _frequency_rows(report: str, heading: str) -> list[tuple[str, int]]:
    """The `| `value` | count |` rows of one table, in the order written.

    `heading` is matched as a prefix: the hex heading carries its own "N of
    M" counts, so its exact wording belongs in the one test that asserts it
    rather than in every caller.
    """
    lines = report.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.startswith(heading)), None)
    assert start is not None, f"no frequency table heading starts {heading!r}"
    rows = []
    for line in lines[start + 1:]:
        match = re.match(r"^\| `([^`]+)` \| (\d+) \|$", line)
        if match:
            rows.append((match.group(1), int(match.group(2))))
        elif rows:
            break
    return rows


def test_civm13_both_frequency_tables_count_the_theme_files_scan():
    """Every assertion here was a self-comparison before this test.

    The gate regenerates and diffs, and the determinism tests compare two
    generations of one fixture, so nothing said what a given input should
    produce. Drop `theme_files` from either frequency loop and both stay green
    while every theme colour leaves the ranked tables. The fixture's theme
    lines, `#abcdef` and `teal`, appear in no other scan, so their presence
    here can only have come through `theme_files`.
    """
    report = color_audit.build_report(SCAN_FIXTURE)
    hex_rows = _frequency_rows(report, "Hex top values")
    named_rows = _frequency_rows(report, "Named top values")

    assert ("#abcdef", 1) in hex_rows, (
        f"the hex table does not count the theme_files scan: {hex_rows}"
    )
    assert ("teal", 1) in named_rows, (
        f"the named table does not count the theme_files scan: {named_rows}"
    )


def test_civm13_the_frequency_tables_hold_every_colour_and_rank_them():
    """Exact rows, in order: a truncated table would otherwise pass.

    `by_count_then_name(...)[:20]` caps the hex table; narrowing that cap
    keeps the report deterministic and self-consistent, so only an assertion
    on the rows can see it. The fixture's ties pin count-then-name order.
    """
    report = color_audit.build_report(SCAN_FIXTURE)

    assert _frequency_rows(report, "Hex top values") == [
        ("#aabbcc", 2), ("#ddeeff", 2), ("#abcdef", 1),
    ], _frequency_rows(report, "Hex top values")
    assert _frequency_rows(report, "Named top values") == [
        ("blue", 2), ("red", 2), ("teal", 1),
    ], _frequency_rows(report, "Named top values")


# --------------------------------------------------------------------------
# CIV-M6 — a scan that has gone blind is not silently accepted
# --------------------------------------------------------------------------

def test_civm6_an_empty_scan_is_refused(monkeypatch):
    """rg exits 1 for "no matches" and for "everything was ignored" alike."""
    monkeypatch.setattr(color_audit, "run_rg", lambda cmd: [])
    with pytest.raises(RuntimeError) as excinfo:
        color_audit.scan_all()
    message = str(excinfo.value)
    assert "returned no lines" in message, message
    assert any(name in message for name in color_audit.SCAN_COMMANDS), (
        f"the error does not say which scan came back empty: {message!r}"
    )


def test_civm6_scan_all_runs_every_scan_with_its_own_command(monkeypatch):
    """Adversarial, two ways.

    A scan_all that always raised would make the gate dead; one that passed
    the same command seven times, or the wrong command for a name, would keep
    both this and the empty-scan test green while the report was built from
    one scan repeated. So the commands are recorded and compared exactly.
    """
    one_line = ['x.py:1:fg_color="#abcdef"']
    calls = []

    def record(cmd):
        calls.append(list(cmd))
        return list(one_line)

    monkeypatch.setattr(color_audit, "run_rg", record)
    result = color_audit.scan_all()

    assert calls == [list(cmd) for cmd in color_audit.SCAN_COMMANDS.values()], calls
    assert set(result) == set(color_audit.SCAN_COMMANDS), result
    assert all(value == one_line for value in result.values()), result


def test_civm6_a_scan_declared_empty_is_allowed(monkeypatch):
    """The escape hatch is a name in a set, not an edit to scan_all."""
    monkeypatch.setattr(color_audit, "run_rg", lambda cmd: [])
    monkeypatch.setattr(
        color_audit, "SCANS_ALLOWED_EMPTY", set(color_audit.SCAN_COMMANDS)
    )
    result = color_audit.scan_all()
    assert set(result) == set(color_audit.SCAN_COMMANDS), result
    assert all(value == [] for value in result.values()), result


# --------------------------------------------------------------------------
# CIV-M7 — run_rg's failure handling, which the happy path never reaches
# --------------------------------------------------------------------------

class _FakeCompleted:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def test_civm7_a_timeout_is_reported_as_a_timeout(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd="rg", timeout=color_audit.RG_TIMEOUT_SECONDS
        )

    monkeypatch.setattr(color_audit.subprocess, "run", raise_timeout)
    with pytest.raises(RuntimeError) as excinfo:
        color_audit.run_rg(["rg", "-n", "x", "."])
    assert "did not finish" in str(excinfo.value), str(excinfo.value)


def test_civm7_stderr_on_a_successful_exit_is_not_discarded(monkeypatch):
    """White-box cover for the complaints branch, on a synthetic result.

    Measured with rg 14.1.1 on 2026-11-11: an unreadable file in a recursive
    scan exits **2**, so it lands in the returncode branch above, not here.
    This covers a complaint arriving with a successful exit, which must not be
    dropped -- and rg has changed that exit code before.
    """
    monkeypatch.setattr(
        color_audit.subprocess, "run",
        lambda *a, **k: _FakeCompleted(
            stdout="a.py:1:x\n", stderr="rg: b.py: Permission denied\n"
        ),
    )
    with pytest.raises(RuntimeError) as excinfo:
        color_audit.run_rg(["rg", "-n", "x", "."])
    assert "may be partial" in str(excinfo.value), str(excinfo.value)
    assert "Permission denied" in str(excinfo.value), str(excinfo.value)


def test_civm7_a_benign_notice_on_stderr_does_not_abort_the_scan(monkeypatch):
    """White-box cover for the allowlist, on a synthetic result.

    Measured with rg 14.1.1 on 2026-11-11: no rg checked here puts a
    binary-file notice on stderr, so the allowlist is defensive and the input
    below is synthetic. It stays because all seven scans share run_rg, and a
    version that did emit one would take them all down together.
    """
    notice = (
        'WARNING: stopped searching binary file ./x.bin after match '
        '(found "\\0" byte around offset 12)\n'
    )
    monkeypatch.setattr(
        color_audit.subprocess, "run",
        lambda *a, **k: _FakeCompleted(stdout="a.py:1:x\n", stderr=notice),
    )
    assert color_audit.run_rg(["rg", "-n", "x", "."]) == ["a.py:1:x"]


def test_civm7_the_scan_is_decoded_as_utf8_and_bounded(monkeypatch):
    """text=True alone decodes by locale: cp1252 on Windows, ASCII under C."""
    seen = {}

    def record(*args, **kwargs):
        seen.update(kwargs)
        return _FakeCompleted(stdout="a.py:1:x\n")

    monkeypatch.setattr(color_audit.subprocess, "run", record)
    color_audit.run_rg(["rg", "-n", "x", "."])
    assert seen.get("encoding") == "utf-8", seen
    assert seen.get("timeout") == color_audit.RG_TIMEOUT_SECONDS, seen


def test_civm7_every_line_of_every_real_scan_can_be_parsed():
    """Covers -n, -H and --no-config behaviourally, which no flag check can.

    Drop -n or -H, or let a ~/.ripgreprc set --heading, and parse_line returns
    None for every line of that scan while the report stays structurally valid
    and short. Every scan, not just one: a directory argument gets a path
    printed for free, while `app_settings` passes a file and parsed 0 of 26.
    """
    failures = {}
    for name, cmd in color_audit.SCAN_COMMANDS.items():
        lines = color_audit.run_rg(cmd)
        unparsed = [ln for ln in lines if color_audit.parse_line(ln) is None]
        if unparsed:
            failures[name] = (len(unparsed), len(lines), unparsed[:2])
    assert failures == {}, (
        "these scans returned lines parse_line could not read, as "
        "{scan: (unparsed, total, examples)}: "
        f"{failures}"
    )


def test_civm14_every_scan_stays_inside_the_declared_paths():
    """The inventory is an audit of UI code, and this is what makes it one.

    A repo-root scan counted documents and this file's own fixtures as the
    app's colour usage: 3 of the `tuples` scan's 5 lines came from here, so
    scan_all's empty-scan guard could be satisfied by test data (2026-11-11).
    It replaces three globs now unreachable. The allowed set names a file, not
    `tools`: color_audit.py's own regexes match HEX_PATTERN.
    """
    trees = ("src/", "themes/")
    files = ("tools/generate_ctk_themes.py",)
    strays = {}
    for name, cmd in color_audit.SCAN_COMMANDS.items():
        outside = sorted({
            e.path
            for ln in color_audit.run_rg(cmd)
            if (e := color_audit.parse_line(ln))
            and not e.path.startswith(trees) and e.path not in files
        })
        if outside:
            strays[name] = outside[:3]
    assert strays == {}, (
        f"these scans reach outside the declared paths, as {{scan: examples}}: "
        f"{strays}. A wider scan reports documents, plans, test fixtures or "
        "this scanner's own regexes as the app's colour usage."
    )


# --------------------------------------------------------------------------
# CIV-M3 — the gate cannot pass vacuously for want of the scanner
# --------------------------------------------------------------------------

def test_civm17_every_tracked_file_in_scope_is_reachable_by_a_scan():
    """`git ls-files` is the independent truth the scans cannot fake."""
    # Every other completeness check here runs the same rg invocations it is
    # checking, so a file rg cannot see is absent from both sides and the
    # check passes. `.gitignore` line 26 ignores `*.json`; its
    # `!src/getmoredone/email_cleaning_rules.json` negation is not applied
    # when rg's walk root is `src`, so that file was unsearchable while
    # `git check-ignore` called it tracked. Measured 2026-11-11: 106 tracked,
    # 105 visible. It holds no colour, so the report was right by luck.
    def listing(*args):
        out = subprocess.run(
            ["rg", "--files", "--sort", "path", "--no-config", *args],
            cwd=REPO_ROOT, capture_output=True, text=True, check=True,
        )
        return set(out.stdout.split())

    def globs(scan):
        """The -g flags really in that command, not a copy of them here."""
        cmd = color_audit.SCAN_COMMANDS[scan]
        return [a for i, a in enumerate(cmd)
                if a == "-g" or (i and cmd[i - 1] == "-g")]

    # Every scan that walks UI_CODE_PATHS must carry the globs, not just the
    # one this test lists files for: the fix's own lesson was to apply it to
    # all five. `app_settings` names a single file, which `-g` does not
    # filter, so it is excluded by name.
    walkers = [n for n, c in color_audit.SCAN_COMMANDS.items()
               if all(path in c for path in color_audit.UI_CODE_PATHS)]
    assert len(walkers) == 5, f"expected 5 recursive src scans, found {walkers}"
    without = [n for n in walkers if globs(n) != list(color_audit.UI_CODE_GLOBS)]
    assert without == [], (
        f"these scans walk {color_audit.UI_CODE_PATHS} without "
        f"UI_CODE_GLOBS: {without}. Each would go blind to the tracked .json "
        "under src/ that the globs exist to reach."
    )

    visible = (listing(*color_audit.UI_CODE_PATHS, *globs("hex"))
               | listing("themes", *globs("theme_files")))
    tracked = subprocess.run(
        ["git", "ls-files", *color_audit.UI_CODE_PATHS, "themes"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    )
    unreachable = sorted(set(tracked.stdout.split()) - visible)
    assert unreachable == [], (
        f"{len(unreachable)} tracked files in the declared scope cannot be "
        f"searched by any scan, so no scan can report them: {unreachable[:5]}. "
        "The inventory claims every colour literal in those paths."
    )


def test_civm18_every_named_colour_a_widget_sets_is_counted():
    """A colour word the list lacks is uncounted, not miscounted."""
    # `NAMED_PATTERN` anchors on the quotes, so `"darkred"` matched no
    # alternative at all -- the two lines carrying it were returned only
    # because of their `hover_color="red"`, and `darkred` reached no table
    # (2026-11-11). This reads the values off the `widget` scan, so a new
    # hard-coded colour word fails here rather than going quietly missing.
    _PROP = (r"(?:fg|hover|text|border|button|progress|selected|highlight)"
             r"_color")
    not_colours = {"transparent"}  # CustomTkinter's "no fill" sentinel
    seen = set()
    for ln in color_audit.run_rg(color_audit.SCAN_COMMANDS["widget"]):
        if entry := color_audit.parse_line(ln):
            seen |= set(re.findall(_PROP + r"""=["']([A-Za-z]+[0-9]*)["']""",
                                   entry.snippet))
            # CustomTkinter's light/dark pair, which the scalar regex cannot
            # see: `fg_color=("gray70", "gray30")` is the form item_editor.py
            # uses, and a pair of unlisted words there would miss the table
            # exactly as `darkred` did. Matched as a strict two-tuple of bare
            # words, because 24 other quoted words on these same lines are
            # semantic tokens (`primary`, `success`) and not colours.
            for pair in re.findall(
                _PROP + r"""=\(\s*["']([A-Za-z]+[0-9]*)["']\s*,"""
                        r"""\s*["']([A-Za-z]+[0-9]*)["']""", entry.snippet):
                seen |= set(pair)
    assert seen, "no bare-word colour in the widget scan; this would be vacuous"
    uncounted = sorted(
        v for v in seen - not_colours
        if not color_audit.NAMED_RE.search(f'"{v}"')
    )
    assert uncounted == [], (
        f"these colour words are set on widgets but match no alternative in "
        f"_NAMED_WORDS, so they reach no frequency table: {uncounted}. Add "
        "them to the word list, or to not_colours above with a reason."
    )


def test_civm19_one_case_policy_across_both_named_scans_and_the_extractor(tmp_path):
    """`-i` on one scan and not the other is a silent divergence."""
    # `named` carried `-i`, `theme_files` carried none, and `NAMED_RE` is
    # `(?i)`: a capitalised colour in a theme file would be extracted but
    # never searched for. Latent on 2026-11-11 (every literal is lowercase),
    # which is why only a written sample can show it.
    def sees(scan, own_paths, sample_file, text):
        sample_file.write_text(text, encoding="utf-8")
        cmd = [a for a in color_audit.SCAN_COMMANDS[scan] if a not in own_paths]
        return bool(color_audit.run_rg(cmd + [str(sample_file)]))

    tmp = tmp_path
    line = 'x = {"fg_color": "GRAY20"}\n'
    extracted = color_audit.NAMED_RE.search('"GRAY20"') is not None
    verdicts = {
        "named": sees("named", color_audit.UI_CODE_PATHS, tmp / "s.py", line),
        "theme_files": sees("theme_files", ("themes",), tmp / "s.json", line),
        "NAMED_RE": extracted,
    }
    assert len(set(verdicts.values())) == 1, (
        f"the two named scans and the extractor disagree on case, as "
        f"{{stage: sees GRAY20}}: {verdicts}. A value one stage sees and "
        "another does not is counted inconsistently."
    )


def test_civm20_the_capped_frequency_table_says_how_much_it_hides():
    """A top-N table that does not say N of M overstates itself."""
    # The hex table ranks 20 of 244 distinct values under the heading "Hex
    # top values:" (2026-11-11), against global rule 6's "N of M".
    report = color_audit.build_report(color_audit.scan_all())
    heading = next(
        (ln for ln in report.splitlines() if ln.startswith("Hex top values")),
        None,
    )
    assert heading, "the report has no hex frequency heading at all"
    shown = len(_frequency_rows(report, heading))
    # The distinct total comes from section 2, which gives every value its
    # own heading -- not from the capped table, where it would equal `shown`
    # and this assertion would pass on "20 of 20".
    distinct = len(re.findall(r"^### `#[0-9a-fA-F]{3,6}`$", report, re.MULTILINE))
    stated = re.match(r"^Hex top values \((\d+) of (\d+) distinct\):$", heading)
    assert stated, (
        f"the hex frequency heading is {heading!r}; it ranks {shown} of "
        f"{distinct} distinct values and must say so (global rule 6)."
    )
    assert (int(stated.group(1)), int(stated.group(2))) == (shown, distinct), (
        f"the hex heading claims {stated.group(1)} of {stated.group(2)}, but "
        f"the table holds {shown} rows and the report {distinct} distinct "
        "hex values."
    )
    # The named table is uncapped, so its heading states one number -- but it
    # states it, rather than a comment in the generator holding a copy that
    # went stale at 37 against a real 40.
    named_head = next(
        (ln for ln in report.splitlines() if ln.startswith("Named top values")),
        None,
    )
    named_stated = re.match(r"^Named top values \(all (\d+) distinct\):$",
                            named_head or "")
    named_rows = len(_frequency_rows(report, "Named top values"))
    named_sections = len(re.findall(r"^### `[a-z][a-z0-9]*`$", report, re.MULTILINE))
    assert named_stated, f"the named frequency heading is {named_head!r}"
    assert int(named_stated.group(1)) == named_rows == named_sections, (
        f"the named heading claims {named_stated.group(1)} distinct values, "
        f"the table holds {named_rows} rows and the report has "
        f"{named_sections} named sections."
    )


def test_civm21_every_occurrence_snippet_renders_as_one_code_span():
    """A backtick in a snippet breaks the row it is wrapped into."""
    # 10 of 1735 rows on 2026-11-11: `md_escape` escaped `|` and nothing
    # else, so a snippet quoting a colour in backticks ended its own span.
    report = color_audit.build_report(color_audit.scan_all())
    broken, checked = [], 0
    for ln in report.splitlines():
        if m := re.match(r"^\| `[^`]+:\d+` \| (.*) \|$", ln):
            checked += 1
            span = m.group(1)
            fence = len(span) - len(span.lstrip("`"))
            body = span[fence:-fence] if fence else span
            if not fence or not span.endswith("`" * fence) or "`" * fence in body:
                broken.append(span[:60])
    # Non-zero, not a floor: a floor here would be arbitrary, and civm2
    # already reddens on any narrowing by diffing the whole report. This
    # only stops the row regex silently matching nothing.
    assert checked, (
        "no occurrence row matched the row shape, so this test would pass "
        "without checking anything"
    )
    assert broken == [], (
        f"{len(broken)} of {checked} occurrence rows do not render as a "
        f"single code span, so the table breaks where they sit: {broken[:3]}"
    )


def test_civm15_gray_scale_literals_reach_the_named_tables():
    """CustomTkinter's grays are colours, and NAMED_PATTERN must see them.

    It matched bare words only, so ``"gray95"`` was invisible: 539 of the 544
    lines holding one, 527 of them theme lines with no other colour
    (2026-11-11). Only the two scans feeding the named tables are asserted,
    since ``widget`` already lists a ``fg_color=("gray70", ...)`` line while
    keeping its values out of the ranked table. One probe per tree, each
    carrying that tree's own ``-g``: without them a probe inherits
    ``.gitignore``'s blanket ``*.json`` and goes blind exactly where the
    scans it checks used to be blind.
    """
    gray = r"""["']gr[ae]y[0-9]{1,3}["']"""
    want = {
        (e.path, e.line)
        for cmd in (color_audit._rg(gray, *color_audit.UI_CODE_PATHS,
                                    *color_audit.UI_CODE_GLOBS),
                    color_audit._rg(gray, "themes", "-g", "*.json"))
        for ln in color_audit.run_rg(cmd)
        if (e := color_audit.parse_line(ln))
    }
    assert want, "no gray-scale literal on disk; this test would be vacuous"
    got = set()
    for name in ("named", "theme_files"):
        for ln in color_audit.run_rg(color_audit.SCAN_COMMANDS[name]):
            if e := color_audit.parse_line(ln):
                got.add((e.path, e.line))
    missing = sorted(want - got)
    assert missing == [], (
        f"{len(missing)} of {len(want)} lines holding a gray-scale literal "
        "are returned by neither `named` nor `theme_files`, so their values "
        f"never reach the frequency tables. First three: {missing[:3]}"
    )
    # Reaching the scan is not reaching the table: the search pattern and the
    # extraction regex are separate, and a line can be returned while its
    # value is dropped. Measured 2026-11-11, the state this caught: all 527
    # theme lines were returned and 0 of their values were ranked.
    values: set[str] = {
        m.group(0).strip("\"'").lower()
        for cmd in (color_audit._rg(gray, *color_audit.UI_CODE_PATHS,
                                    *color_audit.UI_CODE_GLOBS),
                    color_audit._rg(gray, "themes", "-g", "*.json"))
        for ln in color_audit.run_rg(cmd)
        for m in re.finditer(r"""["']gr[ae]y[0-9]{1,3}["']""", ln)
    }
    # Parsed from the value column, not searched as a substring: `gray1`,
    # `gray2` and `gray4` all occur inside `| `gray100` | 18 |`, so a
    # substring check passed for three values that had no row (2026-11-11).
    report = color_audit.build_report(color_audit.scan_all())
    ranked = {v.lower() for v, _ in _frequency_rows(report, "Named top values")}
    absent = sorted(values - ranked)
    assert absent == [], (
        f"{len(absent)} of {len(values)} distinct gray-scale values have no "
        f"row in the named frequency table a reader ranks by: {absent[:5]}"
    )


def test_civm16_the_search_pattern_and_the_extractor_agree():
    """Two regexes for one word list diverged, and the report went quiet.

    `NAMED_PATTERN` searches, `NAMED_RE` extracts the value for the frequency
    tables. They were separate literals until 2026-11-11, when the gray-scale
    fix to the first left the second on bare words: all 527 theme lines were
    returned and none of their values were ranked. Both now derive from
    `_NAMED_WORDS`, and this holds them to it word by word.
    """
    words = color_audit._NAMED_WORDS.split("|")
    assert len(words) == 13, f"word list is {len(words)} long, expected 13"
    broken = {}
    for w in words:
        sample = w.replace("[0-9]{0,3}", "42")
        line = f'''x.py:1:    fg_color="{sample}",'''
        found = re.search(color_audit.NAMED_PATTERN, line) is not None
        got = color_audit.NAMED_RE.search(line)
        if not found or got is None or got.group("c").lower() != sample:
            broken[sample] = (found, got.group("c") if got else None)
    assert broken == {}, (
        "these words disagree between the search pattern and the extractor, "
        f"as {{word: (searched, extracted)}}: {broken}. A word only one of "
        "them knows reaches no frequency table."
    )


def test_civm3_the_generator_names_the_scanner_when_it_is_missing():
    """A bare FileNotFoundError does not tell you to install ripgrep."""
    with pytest.raises(RuntimeError) as excinfo:
        color_audit.run_rg(["color-audit-no-such-binary", "-n", "x", "."])
    message = str(excinfo.value)
    assert "ripgrep" in message.lower(), (
        f"the error does not name what to install: {message!r}"
    )


def test_civm3_the_workflow_installs_the_scanner_the_generator_needs():
    """CI runs the suite, so CI needs rg or the gate above errors there."""
    workflow = (REPO_ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")
    # Anchored to the whole line and compared exactly, not as a substring:
    # `apt-get install -y xvfb  # ripgrep comes from elsewhere` satisfied a
    # substring match, and a floor would hide a package being dropped.
    install_lines = [
        line.strip() for line in workflow.splitlines()
        if re.match(r"^\s*sudo apt-get install\b", line)
    ]
    assert install_lines == ["sudo apt-get install -y xvfb python3-tk ripgrep"], (
        "tests.yml's system-package line is not what the suite needs. ripgrep "
        "is there because tools/color_audit.py shells out to it and the gate "
        f"below regenerates the inventory. Found: {install_lines}"
    )


def test_civm3_ripgrep_is_on_path_here_too():
    """The staleness gate is only meaningful where rg exists."""
    try:
        version_lines = color_audit.run_rg(["rg", "--version"])
    except RuntimeError as exc:
        pytest.fail(f"the colour-inventory gate cannot run here: {exc}")
    assert any("ripgrep" in line for line in version_lines), (
        f"`rg` on PATH does not identify as ripgrep: {version_lines[:1]}"
    )
