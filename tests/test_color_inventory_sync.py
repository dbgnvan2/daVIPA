"""The colour inventory is generated, so it can drift; these keep it honest.

``docs/ui_color_inventory.md`` is written by ``tools/color_audit.py`` and read
by people, not by code. Nothing ran the generator between 18dbe02 and
2026-11-11, and by then the committed file was 3,250 lines out of date and
still asserted a colour rule the project had retired. A generated document
with no gate is a document that is wrong and says nothing about it.

A gate like this only works if the generator is deterministic, and it was not:
four sections of the report came out in whatever order ripgrep's threads
produced, so two runs over an unchanged tree disagreed. The determinism tests
come first here because the staleness test is built on them.

Spec:  no spec file -- four criteria, no user-visible behaviour (CLAUDE.md,
       *Records are filed, not tested*).
Tests: this file.
"""

from __future__ import annotations

import random
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.meta

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import color_audit  # noqa: E402  (needs the path above)


# A hand-built stand-in for a scan, small enough to reason about and shaped to
# hit every ordering decision build_report makes:
#   * `#aabbcc` and `#ddeeff` tie at two hex occurrences each
#   * "red" and "blue" tie at two named occurrences each
#   * app_settings and tuples carry three lines apiece, out of path order
# A tie is the only place insertion order can leak into the output, so a
# fixture without one would pass against the bug.
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
    "theme_files": [],
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


# --------------------------------------------------------------------------
# CIV-M2 — a stale inventory fails the suite
# --------------------------------------------------------------------------

def test_civm2_the_committed_inventory_matches_a_fresh_generation():
    """The gate. Regenerate after any change that adds or removes a colour."""
    committed = color_audit.DEFAULT_OUTPUT
    assert committed.exists(), f"{committed} is missing"

    scans = {
        name: color_audit.run_rg(cmd)
        for name, cmd in color_audit.SCAN_COMMANDS.items()
    }
    fresh = color_audit.build_report(scans)
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
            "and commit the result. It is generated -- do not edit it by hand."
        )


# --------------------------------------------------------------------------
# CIV-M3 — the gate cannot pass vacuously for want of the scanner
# --------------------------------------------------------------------------

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
    apt_lines = [
        line for line in workflow.splitlines()
        if "apt-get install" in line and not line.strip().startswith("#")
    ]
    assert apt_lines, "tests.yml no longer installs system packages"
    assert any("ripgrep" in line for line in apt_lines), (
        "tests.yml does not install ripgrep, which tools/color_audit.py shells "
        f"out to. apt-get lines found: {apt_lines}"
    )


def test_civm3_ripgrep_is_on_path_here_too():
    """The staleness gate is only meaningful where rg exists."""
    result = subprocess.run(
        ["rg", "--version"], capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        "ripgrep is not on PATH, so the inventory gate cannot run. "
        "Install it (brew install ripgrep)."
    )
