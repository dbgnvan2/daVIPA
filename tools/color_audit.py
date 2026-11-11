#!/usr/bin/env python3
"""Generate docs/ui_color_inventory.md from deterministic ripgrep scans.

Usage:
  ./venv/bin/python tools/color_audit.py
"""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "ui_color_inventory.md"

HEX_PATTERN = "#[0-9a-fA-F]{6}\\b|#[0-9a-fA-F]{3}\\b"
NAMED_PATTERN = (
    r'"(darkgreen|green|red|orange|blue|teal|cyan|yellow|white|black|gray|grey)"'
    r"|'(darkgreen|green|red|orange|blue|teal|cyan|yellow|white|black|gray|grey)'"
)

# The inventory is this scan's own output; feeding it back in would compound.
_NOT_SELF = ("-g", "!docs/ui_color_inventory.md")
# themes/*.json is scanned once, by `theme_files`, whose pattern covers hex and
# named together. Without this the "." scans cover the same bytes and every
# theme colour reaches the frequency tables twice. Measured 2026-11-11 before
# the fix: `#000000` read 79 in the frequency table against 57 rows in the
# occurrence table below it, the 22 of difference being the theme files
# counted a second time. Those are that day's figures and not an invariant --
# the scan is repo-wide, so any file that merely mentions a colour moves
# them, this comment included.
# Tests: tests/test_color_inventory_sync.py::test_civm5_the_scans_feeding_one_count_do_not_overlap
_NOT_THEMES = ("-g", "!themes/**")
# The staleness gate's fixtures are hand-written stand-ins for rg output, so
# they look exactly like colour usage to these scans and were counted as it:
# measured on 2026-11-11, before this exclusion, 3 of the 5 lines the
# `tuples` scan returned came from that one file, which
# meant `scan_all`'s refusal of an empty scan -- the only guard here against a
# scan going blind -- could be held above zero by test data alone. This is the
# same self-reference as `_NOT_SELF`, not a narrowing of what the scan covers.
# Tests: tests/test_color_inventory_sync.py::test_civm7_no_scan_reads_this_gate_s_own_fixtures
_NOT_GATE = ("-g", "!tests/test_color_inventory_sync.py")


def _rg(*args: str) -> List[str]:
    """A scan command carrying the flags every scan must have.

    ``--sort path``: rg searches in parallel and promises no output order,
    which the staleness gate cannot tolerate.
    ``--no-config``: ``RIPGREP_CONFIG_PATH`` or a developer's ``~/.ripgreprc``
    can set ``--heading`` or ``--no-line-number``, and then ``parse_line``
    returns ``None`` for every line and the report comes out structurally
    valid and almost entirely empty.
    ``-H``: rg prints the filename only when searching more than one file, so
    ``app_settings`` -- the one scan given an explicit path -- emitted
    ``55:    appearance_mode...`` and parsed 0 of its 26 lines. The report
    still built: ``scan_line_key`` fell back to ordering the raw string and
    the AppSettings block came out lexical (445, 446, 447, 55, 56, 626),
    which is the ordering that function exists to prevent.
    Tests: tests/test_color_inventory_sync.py::test_civm7_every_line_of_every_real_scan_can_be_parsed
    """
    return ["rg", "--sort", "path", "--no-config", "-n", "-H", *args]


SCAN_COMMANDS: Dict[str, List[str]] = {
    "widget": _rg(
        "fg_color=|hover_color=|text_color=|border_color=|button_color=|progress_color=|selected_color=|corner_radius=|highlight_color=",
        ".", *_NOT_SELF, *_NOT_GATE,
    ),
    "hex": _rg(HEX_PATTERN, ".", *_NOT_SELF, *_NOT_THEMES, *_NOT_GATE),
    "named": _rg("-i", NAMED_PATTERN, ".", *_NOT_SELF, *_NOT_THEMES, *_NOT_GATE),
    "theme_api": _rg(
        "set_default_color_theme\\(|set_appearance_mode\\(",
        ".", *_NOT_SELF, *_NOT_GATE,
    ),
    "tuples": _rg(
        "(fg_color|hover_color|text_color|border_color|button_color|progress_color|selected_color|highlight_color)\\s*=\\s*(\\(|\\[)",
        ".", *_NOT_SELF, *_NOT_GATE,
    ),
    "app_settings": _rg(
        "color|theme|appearance_mode|theme_name|drag_schedule_date_text_color|color_hex",
        "src/getmoredone/app_settings.py",
    ),
    "theme_files": _rg(f"{HEX_PATTERN}|{NAMED_PATTERN}", "themes", "-g", "*.json"),
}

HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
NAMED_RE = re.compile(
    r"(?i)(?:\"|')(?P<c>darkgreen|green|red|orange|blue|teal|cyan|yellow|white|black|gray|grey)(?:\"|')"
)
WIDGET_PROP_RE = re.compile(
    r"(fg_color|hover_color|text_color|border_color|button_color|progress_color|selected_color|corner_radius|highlight_color)="
)


@dataclass(frozen=True)
class Entry:
    path: str
    line: int
    snippet: str


RG_TIMEOUT_SECONDS = 120

# Defensive, not load bearing. Measured with rg 14.1.1 on 2026-11-11: a
# recursive scan skips a binary file in silence, and an explicit binary
# argument writes `binary file matches (...)` to *stdout* with no WARNING
# prefix -- so no rg checked here puts this on stderr at all. It stays because
# all seven scans share run_rg, and on a version that does emit a benign
# notice one matching binary file would abort every one of them with a message
# blaming a partial scan.
RG_BENIGN_STDERR = re.compile(r"^WARNING: stopped searching binary file ")

# Scans allowed to return nothing, by name. Declaring one is a reviewable
# one-line change here rather than an edit to scan_all's logic (global rule 8).
# `tuples` is the scan nearest to empty. Its current count is in the per-scan
# table of the generated report, which is the figure to read rather than one
# copied out of it to here -- adding `_NOT_GATE` below took it from 5 to 2 and
# left this line stating 5. On 2026-11-11 it returned two lines, one of them a
# false positive on a parenthesised assignment, so migrating the single real
# colour tuple -- which section 3 of the report recommends -- is what would
# empty this scan and make a declaration here necessary.
SCANS_ALLOWED_EMPTY: set = set()


def run_rg(cmd: Sequence[str]) -> List[str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            # Without an explicit encoding, text=True decodes through the
            # locale -- cp1252 on Windows, which this repo supports, and ASCII
            # under LC_ALL=C. 22 lines of the inventory are non-ASCII, so that
            # is a UnicodeDecodeError or mojibake, and the gate would then fail
            # for the environment while its message blamed staleness.
            encoding="utf-8",
            errors="replace",
            timeout=RG_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"rg did not finish within {RG_TIMEOUT_SECONDS}s: {shlex.join(list(cmd))}. "
            "--sort path disables rg's parallelism, so this scan is slower than "
            "an unsorted one."
        ) from exc
    except FileNotFoundError as exc:
        # A bare FileNotFoundError names the binary and not the remedy, and
        # this generator is the only thing in the repo that needs ripgrep.
        # Tests: tests/test_color_inventory_sync.py::test_civm3_the_generator_names_the_scanner_when_it_is_missing
        raise RuntimeError(
            f"{cmd[0]!r} is not on PATH. tools/color_audit.py scans with "
            "ripgrep: install it (`brew install ripgrep`, or `apt-get install "
            "ripgrep`) and run this again."
        ) from exc
    # rg returns 1 for no matches, which is fine, and 2 for a search error.
    # Measured with rg 14.1.1 on 2026-11-11: an unreadable file in a recursive
    # scan exits 2 and so arrives *here*, not at the stderr branch below.
    # A symlink is not that case. rg does not follow one without -L, so in a
    # recursive scan a symlink -- broken or working -- is skipped in silence
    # at exit 0 and reaches neither branch; only naming one as the search
    # argument exits 2. No scan here passes -L and the repo tracks no symlink
    # (`git ls-files -s` holds no mode 120000), so nothing is missing from the
    # inventory today, but a symlink added under a scanned path would be
    # dropped without a word.
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"Command failed ({result.returncode}): {shlex.join(list(cmd))}\n"
            f"{result.stderr.strip()}"
        )
    # A per-file complaint that arrives with a *successful* exit must not be
    # dropped: discarding it made a partial scan look like a clean one, which
    # is a shorter inventory with no signal attached. rg 14.1.1 exits 2 for
    # the unreadable-file case, so it is the branch above that catches that
    # today; this one is here because rg has already changed its exit code for
    # a per-file error once, and a silent partial scan is the costly failure.
    complaints = [
        line for line in result.stderr.splitlines()
        if line.strip() and not RG_BENIGN_STDERR.match(line.strip())
    ]
    if complaints:
        raise RuntimeError(
            "rg reported errors, so this scan may be partial:\n"
            + "\n".join(complaints)
            + f"\ncommand: {shlex.join(list(cmd))}"
        )
    return [ln for ln in result.stdout.splitlines() if ln.strip()]


def scan_all() -> Dict[str, List[str]]:
    """Run every scan, refusing one that came back empty.

    rg exits 1 both for "no matches" and for "every candidate file was
    excluded by an ignore rule", and ``run_rg`` treats 1 as success. That
    makes a scan which has gone blind indistinguishable from one that found
    nothing. It is a live hazard rather than a hypothetical: ``.gitignore``
    holds a blanket ``*.json`` off ``themes/`` with two negations, and losing
    them empties the ``theme_files`` scan, drops 765 lines from the inventory
    and leaves the staleness gate green from the next regeneration onward.
    Every scan matches something today.

    Tests: tests/test_color_inventory_sync.py::test_civm6_an_empty_scan_is_refused
    """
    results: Dict[str, List[str]] = {}
    for name, cmd in SCAN_COMMANDS.items():
        found = run_rg(cmd)
        if not found and name not in SCANS_ALLOWED_EMPTY:
            raise RuntimeError(
                f"the {name!r} scan returned no lines. rg cannot tell "
                "'nothing matches' apart from 'an ignore rule hid every "
                "candidate file', so this is either a real emptying -- in "
                "which case add it to SCANS_ALLOWED_EMPTY -- or a scan that "
                "has gone blind. "
                f"command: {shlex.join(list(cmd))}"
            )
        results[name] = found
    return results


def scan_line_key(line: str) -> Tuple[str, int, str]:
    """Order raw rg output by file, then line number, then text.

    Lexical order would put ``:100:`` before ``:9:``; an unparseable line
    sorts by its own text rather than being dropped.
    """
    entry = parse_line(line)
    if entry is None:
        return (line, 0, "")
    return (entry.path, entry.line, entry.snippet)


def by_count_then_name(counter: Counter) -> List[Tuple[str, int]]:
    """Most frequent first, ties broken by colour name.

    ``Counter.most_common`` breaks ties by insertion order, which here is
    ripgrep's output order, which is thread scheduling. Two runs over an
    unchanged tree disagreed because of this.
    """
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))


def parse_line(line: str) -> Entry | None:
    parts = line.split(":", 2)
    if len(parts) < 3:
        return None
    path, line_s, snippet = parts
    if path.startswith("./"):
        path = path[2:]
    try:
        line_no = int(line_s)
    except ValueError:
        return None
    return Entry(path=path, line=line_no, snippet=snippet.strip())


def md_escape(value: str) -> str:
    return value.replace("|", "\\|")


def build_report(lines: Dict[str, List[str]]) -> str:
    hex_occ: List[str] = []
    named_occ: List[str] = []

    for src in ("hex", "theme_files"):
        for line in lines[src]:
            hex_occ.extend(color.lower() for color in HEX_RE.findall(line))

    for src in ("named", "theme_files"):
        for line in lines[src]:
            named_occ.extend(match.group("c").lower() for match in NAMED_RE.finditer(line))

    widget_props = Counter()
    for line in lines["widget"]:
        for prop in WIDGET_PROP_RE.findall(line):
            widget_props[prop] += 1

    occurrences: Dict[str, List[Entry]] = defaultdict(list)
    seen: set[Tuple[str, str, int, str]] = set()

    for src in ("hex", "named", "theme_files"):
        for line in lines[src]:
            entry = parse_line(line)
            if not entry:
                continue
            color_values = [h.lower() for h in HEX_RE.findall(line)]
            color_values.extend(m.group("c").lower() for m in NAMED_RE.finditer(line))
            for value in color_values:
                key = (value, entry.path, entry.line, entry.snippet)
                if key in seen:
                    continue
                seen.add(key)
                occurrences[value].append(entry)

    for value in list(occurrences):
        occurrences[value] = sorted(occurrences[value], key=lambda e: (e.path, e.line, e.snippet))

    theme_api_entries = sorted(
        (entry for entry in (parse_line(line) for line in lines["theme_api"]) if entry),
        key=lambda e: (e.path, e.line),
    )
    tuple_entries = sorted(
        (entry for entry in (parse_line(line) for line in lines["tuples"]) if entry),
        key=lambda e: (e.path, e.line),
    )

    out: List[str] = []
    out.append("# UI Color Inventory")
    out.append("")
    out.append("Generated via deterministic `rg` scans from repo root.")
    out.append("")
    out.append("## Scan Commands")
    out.append("")
    out.append(
        "Rendered from `SCAN_COMMANDS` in `tools/color_audit.py`, so what is "
        "printed here is what produced this file. The four hand-written lines "
        "this replaced had drifted: they omitted three of the seven scans and "
        "every flag."
    )
    out.append("")
    out.append("```bash")
    for name, cmd in SCAN_COMMANDS.items():
        out.append(f"# {name}")
        out.append(shlex.join(cmd))
    out.append("```")
    out.append("")
    out.append("## 1) Summary Counts By Type")
    out.append("")
    out.append(f"- Hex colors (match count): **{len(hex_occ)}**")
    out.append(f"- Named colors (match count): **{len(named_occ)}**")
    out.append(f"- Tuple colors / appearance tuples (match count): **{len(lines['tuples'])}**")
    out.append(
        "- CustomTkinter theme API usage (`set_default_color_theme`/`set_appearance_mode`) "
        f"line count: **{len(lines['theme_api'])}**"
    )
    out.append(f"- Widget explicit overrides (line count): **{len(lines['widget'])}**")
    out.append("")
    out.append("Lines returned per scan. `scan_all` refuses an empty scan, so")
    out.append("this table is not the blindness check -- it is here to localise")
    out.append("a diff to one scan, and because section 1 omits the hex, named")
    out.append("and theme_files line counts.")
    out.append("")
    out.append("| Scan | Lines |")
    out.append("|---|---:|")
    for name in sorted(lines):
        out.append(f"| `{name}` | {len(lines[name])} |")
    out.append("")
    out.append("Widget override property breakdown:")
    out.append("")
    out.append("| Property | Count |")
    out.append("|---|---:|")
    for prop, count in sorted(widget_props.items()):
        out.append(f"| `{prop}` | {count} |")
    out.append("")
    out.append("AppSettings persisted color/theme fields:")
    out.append("")
    out.append("```text")
    out.extend(sorted(lines["app_settings"], key=scan_line_key))
    out.append("```")
    out.append("")
    out.append("Hex top values:")
    out.append("")
    out.append("| Color | Count |")
    out.append("|---|---:|")
    for color, count in by_count_then_name(Counter(hex_occ))[:20]:
        out.append(f"| `{color}` | {count} |")
    out.append("")
    out.append("Named top values:")
    out.append("")
    out.append("| Color | Count |")
    out.append("|---|---:|")
    for color, count in by_count_then_name(Counter(named_occ)):
        out.append(f"| `{color}` | {count} |")
    out.append("")
    out.append("## 2) Complete Occurrence Table (Grouped by Color Value, then File)")
    out.append("")
    out.append("Each row is from grep output and includes `file:line` and a short snippet.")
    out.append("")
    for color in sorted(occurrences.keys()):
        out.append(f"### `{color}`")
        out.append("")
        out.append("| File:Line | Snippet |")
        out.append("|---|---|")
        for entry in occurrences[color]:
            snippet = md_escape(entry.snippet)[:180]
            out.append(f"| `{entry.path}:{entry.line}` | `{snippet}` |")
        out.append("")

    out.append("### Theme API Occurrences")
    out.append("")
    out.append("| File:Line | Snippet |")
    out.append("|---|---|")
    for entry in theme_api_entries:
        snippet = md_escape(entry.snippet)[:200]
        out.append(f"| `{entry.path}:{entry.line}` | `{snippet}` |")
    out.append("")

    out.append("### Tuple / Appearance Tuple Occurrences")
    out.append("")
    out.append("| File:Line | Snippet |")
    out.append("|---|---|")
    for entry in tuple_entries:
        snippet = md_escape(entry.snippet)[:200]
        out.append(f"| `{entry.path}:{entry.line}` | `{snippet}` |")
    out.append("")

    out.append("## 3) Replace Plan")
    out.append("")
    out.append("Recommended migration targets:")
    out.append("")
    out.append("- **Theme defaults (JSON-driven):**")
    out.append("- Base CTk widget palette defaults (`CTkButton`, `CTkFrame`, `CTkEntry`, `CTkCheckBox`, `CTkSwitch`, etc.) should stay in `/themes/*.json`.")
    out.append("- Remove one-off color literals that duplicate core palette choices.")
    out.append("- **Semantic tokens (code-level):**")
    out.append("- Route UI state colors through semantic names in `src/getmoredone/theme.py` (e.g., `primary`, `primary_hover`, `ghost_hover`, `selected_tint`, `critical_tint`, `success_tint`, `muted_text`, `border`).")
    out.append("- Convert direct `fg_color`/`hover_color`/`text_color` literals in screens to semantic token lookups.")
    out.append("- **Allowed data-driven colors:**")
    out.append("- Keep `segment_descriptions.color_hex` as the only domain data-driven color source.")
    out.append("- A segment color may fill a row only where that row's foreground is derived from it for contrast (`priority_levels.row_fill`); everywhere else keep it to accent/chip/stripe/icon usage.")
    out.append("- **Persisted settings:**")
    out.append("- Keep only settings-level color fields that are user-configurable and intentional (`drag_schedule_date_text_color`) plus theme selectors (`appearance_mode`, `theme_name`).")
    out.append("")
    out.append("## 4) Hard Rule")
    out.append("")
    out.append("**No new hard-coded colors except data-driven segment colors (`segment_descriptions.color_hex`).**")
    out.append("")
    out.append("Enforcement recommendation: run the same `rg` commands in CI and diff this inventory after refactors.")
    out.append("")

    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    scan_results = scan_all()

    report = build_report(scan_results)
    output_path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n": the default translates to CRLF on Windows, which this repo
    # supports, and the gate compares the bytes.
    output_path.write_text(report, encoding="utf-8", newline="\n")

    print(f"Wrote {output_path}")
    print(f"Hex matches: {len(scan_results['hex'])}")
    print(f"Named matches: {len(scan_results['named'])}")
    print(f"Widget override lines: {len(scan_results['widget'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
