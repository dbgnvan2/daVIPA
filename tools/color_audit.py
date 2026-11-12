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
# CustomTkinter's grays carry a lightness suffix (`gray95`), which a bare-word
# list missed: 539 of the 544 lines holding one, 527 of them in themes/ with no
# other colour, so they appeared nowhere at all. Measured 2026-11-11.
# Tests: tests/test_color_inventory_sync.py::test_civm15_gray_scale_literals_reach_the_named_tables
_NAMED_WORDS = (
    "darkgreen|green|darkred|red|orange|blue|teal|cyan|yellow|white|black"
    "|gray[0-9]{0,3}|grey[0-9]{0,3}"
)
NAMED_PATTERN = rf'"({_NAMED_WORDS})"' + rf"|'({_NAMED_WORDS})'"

# Scope (CIV-A1, 2026-11-11): the UI code, the themes it loads, and the tool
# that writes them. A repo-root scan counted documents and this gate's own
# fixtures as the app's colour usage; narrowing dropped 437 of 1953
# occurrences and the generator put 37 back. Named as a file, not as `tools`,
# because color_audit.py's own regexes match HEX_PATTERN. `assets/icons/*.svg`
# stays uninventoried. Why, in full:
# docs/unused-docs/changes/2026-11-11-colour-inventory-scope.md
# Tests: tests/test_color_inventory_sync.py::test_civm14_every_scan_stays_inside_the_declared_paths
# Tests: tests/test_color_inventory_sync.py::test_civm5_the_scans_feeding_one_count_do_not_overlap
UI_CODE_PATHS = ("src", "tools/generate_ctk_themes.py")

# `.gitignore` line 26 ignores `*.json`, and its
# `!src/getmoredone/email_cleaning_rules.json` negation is flat, so it is not
# applied when rg's walk root is `src` itself: the file was unsearchable while
# `git check-ignore` reported it tracked. 106 tracked files in scope, 105
# visible (2026-11-11). A positive `-g` overrides `.gitignore` outright, which
# is the same reason `theme_files` can read `themes/*.json` at all. Naming the
# extensions also bounds the walk, and the test below fails if a tracked file
# in scope falls outside them.
# Tests: tests/test_color_inventory_sync.py::test_civm17_every_tracked_file_in_scope_is_reachable_by_a_scan
UI_CODE_GLOBS = ("-g", "*.py", "-g", "*.json")


def _rg(*args: str) -> List[str]:
    """A scan command carrying the flags every scan must have.

    ``--sort path``: rg searches in parallel and promises no output order,
    which the staleness gate cannot tolerate. It also settles *which* files
    are searched -- an unsorted run raced on ``.gitignore``'s whitelists and
    returned 11 lines on 6 of 10 runs and 0 on the other 4 -- so this flag is
    load-bearing twice over.
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
        *UI_CODE_PATHS, *UI_CODE_GLOBS,
    ),
    "hex": _rg(HEX_PATTERN, *UI_CODE_PATHS, *UI_CODE_GLOBS),
    "named": _rg("-i", NAMED_PATTERN, *UI_CODE_PATHS, *UI_CODE_GLOBS),
    "theme_api": _rg(
        "set_default_color_theme\\(|set_appearance_mode\\(",
        *UI_CODE_PATHS, *UI_CODE_GLOBS,
    ),
    "tuples": _rg(
        "(fg_color|hover_color|text_color|border_color|button_color|progress_color|selected_color|highlight_color)\\s*=\\s*(\\(|\\[)",
        *UI_CODE_PATHS, *UI_CODE_GLOBS,
    ),
    "app_settings": _rg(
        "color|theme|appearance_mode|theme_name|drag_schedule_date_text_color|color_hex",
        "src/getmoredone/app_settings.py",
    ),
    # `-i` matches `named` above and `NAMED_RE`'s `(?i)` below. It was absent
    # here, so a capitalised colour in a theme file would have been extracted
    # by a scan that never searched for it. Latent -- every literal on disk is
    # lowercase, so the counts are identical either way (2026-11-11).
    # Tests: tests/test_color_inventory_sync.py::test_civm19_one_case_policy_across_both_named_scans_and_the_extractor
    "theme_files": _rg(
        "-i", f"{HEX_PATTERN}|{NAMED_PATTERN}", "themes", "-g", "*.json",
    ),
}

# Compiled from the same source as the scan patterns, not retyped. They were
# separate literals, and the gray-scale fix to NAMED_PATTERN left this one on
# bare words: all 527 theme lines were returned and none of their values were
# ranked (2026-11-11). One operation, one definition (global rule 5).
# Tests: tests/test_color_inventory_sync.py::test_civm16_the_search_pattern_and_the_extractor_agree
HEX_RE = re.compile(HEX_PATTERN)
NAMED_RE = re.compile(rf"""(?i)["'](?P<c>{_NAMED_WORDS})["']""")
WIDGET_PROP_RE = re.compile(
    r"(fg_color|hover_color|text_color|border_color|button_color|progress_color|selected_color|corner_radius|highlight_color)="
)


@dataclass(frozen=True)
class Entry:
    path: str
    line: int
    snippet: str


RG_TIMEOUT_SECONDS = 120

# Defensive, not load bearing: measured with rg 14.1.1 on 2026-11-11, no scan
# here puts a binary-file notice on stderr at all. Kept because a version that
# did would abort all seven over one matching binary file.
RG_BENIGN_STDERR = re.compile(r"^WARNING: stopped searching binary file ")

# Scans allowed to return nothing, by name. A declaration here is a reviewable
# one-line change rather than an edit to scan_all's logic (global rule 8). Read
# the report's per-scan table for current counts, not a figure copied to here.
# `tuples` holds 2 lines, one a false positive on a parenthesised assignment
# that is not going away, so migrating the real tuple leaves 1, not 0.
SCANS_ALLOWED_EMPTY: set = set()


def run_rg(cmd: Sequence[str]) -> List[str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            # Without this, text=True decodes through the locale (cp1252 on
            # Windows, ASCII under LC_ALL=C); 22 inventory lines are non-ASCII.
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
        # A bare FileNotFoundError names the binary, not the remedy.
        # Tests: tests/test_color_inventory_sync.py::test_civm3_the_generator_names_the_scanner_when_it_is_missing
        raise RuntimeError(
            f"{cmd[0]!r} is not on PATH. tools/color_audit.py scans with "
            "ripgrep: install it (`brew install ripgrep`, or `apt-get install "
            "ripgrep`) and run this again."
        ) from exc
    # rg returns 1 for no matches, 2 for a search error. Measured with rg
    # 14.1.1 on 2026-11-11: an unreadable file in a recursive scan exits 2 and
    # arrives here, not at the stderr branch below. Symlinks: without -L one
    # inside a scanned tree is skipped silently at exit 0, while a *working*
    # one named as a search path is followed -- so a symlinked `src` would be
    # scanned through with test_civm14 green. The repo tracks none today.
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"Command failed ({result.returncode}): {shlex.join(list(cmd))}\n"
            f"{result.stderr.strip()}"
        )
    # A per-file complaint on a *successful* exit must not be dropped: it made
    # a partial scan look clean, a shorter inventory with no signal attached.
    # rg has changed its exit code for a per-file error once before.
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


# The hex table is capped and the named one is not: 244 distinct hex values
# against 37 named (2026-11-11). The heading states both numbers, so the cap
# announces what it drops (global rule 6).
# Tests: tests/test_color_inventory_sync.py::test_civm20_the_capped_frequency_table_says_how_much_it_hides
HEX_TOP_N = 20


def md_code(value: str, limit: int) -> str:
    """One inline code span holding `value`, truncated to `limit` first.

    A snippet is quoted source, so it can hold backticks and pipes. `|` needs
    escaping even inside a code span, because the row's cells are
    pipe-separated; a backtick needs a fence longer than the longest run
    inside it, plus a space of padding when the text starts or ends with one.
    Escaping only `|` left 10 of 1735 rows broken (2026-11-11). Truncating
    before escaping, not after, is what keeps a `\\|` from being cut in half.
    Tests: tests/test_color_inventory_sync.py::test_civm21_every_occurrence_snippet_renders_as_one_code_span
    """
    text = value[:limit].replace("|", "\\|")
    fence = "`" * (max((len(run) for run in re.findall("`+", text)), default=0) + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return f"{fence}{pad}{text}{pad}{fence}"


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
    out.append(
        "Generated via deterministic `rg` scans of `src/`, `themes/` and "
        "`tools/generate_ctk_themes.py`: the UI code, the themes it loads, "
        "and the tool that writes them (CIV-A1, 2026-11-11)."
    )
    out.append("")
    out.append(
        "Not covered: the tests, documents and plans that mention colours, "
        "and the named colours inside `assets/icons/*.svg`."
    )
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
    hex_ranked = by_count_then_name(Counter(hex_occ))
    out.append(
        f"Hex top values ({min(HEX_TOP_N, len(hex_ranked))} of "
        f"{len(hex_ranked)} distinct):"
    )
    out.append("")
    out.append("| Color | Count |")
    out.append("|---|---:|")
    for color, count in hex_ranked[:HEX_TOP_N]:
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
            snippet = md_code(entry.snippet, 180)
            out.append(f"| `{entry.path}:{entry.line}` | {snippet} |")
        out.append("")

    out.append("### Theme API Occurrences")
    out.append("")
    out.append("| File:Line | Snippet |")
    out.append("|---|---|")
    for entry in theme_api_entries:
        snippet = md_code(entry.snippet, 200)
        out.append(f"| `{entry.path}:{entry.line}` | {snippet} |")
    out.append("")

    out.append("### Tuple / Appearance Tuple Occurrences")
    out.append("")
    out.append("| File:Line | Snippet |")
    out.append("|---|---|")
    for entry in tuple_entries:
        snippet = md_code(entry.snippet, 200)
        out.append(f"| `{entry.path}:{entry.line}` | {snippet} |")
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
