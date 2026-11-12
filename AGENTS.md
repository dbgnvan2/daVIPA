# Working agreements (daVIPA)

> **The three-agent branch workflow this file used to describe is retired.**
> `codex/agent-docs` and `codex/agent-github` were never created as branches,
> and `codex/agent-code` was last touched 2026-04-03, 624 commits behind
> `main` and an ancestor of it (re-measured 2026-11-09). Work happens on `main`, or on a feature branch merged into it. The
> requirements below are retained because they were never about the agent
> split — they are about not losing context between sessions.

## One build batch at a time

Only one session builds in this checkout at a time. A working tree has one git
index, so concurrent writers race on it however the sessions are related. A
session running alongside a build is read-only: it commits nothing and stages
nothing.

**There is no second build, and no worktree exception.** Two concurrent builds
in separate worktrees, their file sets checked for overlap before either
started, used to be allowed here. That was withdrawn on 2026-11-08, because
worktrees fixed the shared index and not
the thing that cost more: work finished and left on a branch, with `main`
holding the tests for code it did not contain. The rule, and what four
concurrent batches cost that day, are in `CLAUDE.md` under *Working agreements
→ One build batch at a time*, which carries the withdrawal as one of its
bullets. The heading *Why the worktree exception was withdrawn* that this
pointer used to name is gone; its measurements are filed in
`docs/unused-docs/changes/2026-11-10-claude-md-narrative.md`.

## Handoff notes

A note is written when it carries something a commit message cannot, not once
per batch. The conditions, and why the per-batch requirement was dropped on
2026-11-09, are in `CLAUDE.md` under *Working agreements → Records are filed,
not tested* — stated there and not restated here, because a second copy of a
rule drifts from the first.

Where one is written: `docs/unused-docs/changes/<yyyy-mm-dd>-<topic>.md`,
template `.agents/templates/handoff-note.md`, fields summary, files changed,
test/verification status, follow-ups.

## Docs sync

If code behaviour, UI text, CLI flags, or dependencies changed, docs and the
requirements files must be updated in the same change. A file under
`docs/unused-docs/` is not that change: filing history does not keep a
document current. Enforced by `tests/test_docs_sync_rule.py`, which asserts
`tools/agents/check_docs_sync.py::verdict` over fixtures, so the rule fails
locally and in `tests.yml` before a push. Both `requirements.txt` and
`requirements-dev.txt` count as dependency files. To apply it to real changes,
run `./venv/bin/python tools/agents/check_docs_sync.py` by hand; a range it
cannot read reports as *skipped*, not as a pass.

This was the workflow `agent-docs-gate.yml` until 2026-11-09. That
workflow triggered on `pull_request` only, this repo opens none, and so it had
never run — `SAG-A3`.

## Merge gates

- tests pass (`.github/workflows/tests.yml`), which runs the docs-sync rule's
  decision function over fixtures with the rest of the suite — it does not
  diff the change, so see the paragraph above for the command that does
- UI regression coverage satisfied (per `docs/AGENT_UI_REGRESSION_POLICY.md`)

## UI Regression Guardrail

Follow `docs/AGENT_UI_REGRESSION_POLICY.md` for any UI change. Existing
user-visible controls are part of the contract and must not be removed, hidden,
renamed, or relocated without explicit approval and regression coverage. Before
modifying any existing UI, identify the current user-visible actions and
preserve them.

---

# daVIPA — UI Theme System (CustomTkinter)

## Goal
Implement a cohesive UI color system with low runtime overhead by:
1) using CustomTkinter custom theme JSON for global widget defaults, and
2) using a small set of semantic color tokens for UI states (selection, danger, etc.)

## Tech constraints
- UI framework: CustomTkinter.
- Use CustomTkinter custom theme JSON files loaded via:
  customtkinter.set_default_color_theme("path/to/theme.json")
- Appearance mode values must be one of: "system", "dark", "light".

## Theme architecture
- Create /themes directory with >= 2 theme json files (e.g., graphite.json, ocean.json).
- Add user settings:
  - appearance_mode: "system" | "dark" | "light"
  - theme_name: string mapped to a theme json path
- On app startup:
  - load AppSettings first
  - call set_appearance_mode(settings.appearance_mode)
  - call set_default_color_theme(path_for_theme_name)

## Semantic color rules
- Reduce color noise: only 1 “primary” color for main action emphasis.
- “Success/Warning/Danger” colors are for status only (not decoration).
- Segment/category colors from data (e.g., segment_descriptions.color_hex) may
  fill a row only where every foreground on that row is derived from the fill
  for contrast -- text at 4.5:1, non-text controls at 3:1. That path is
  `priority_levels.row_fill` with `pick_text_color` and `row_control_kwargs`,
  and Today, Upcoming and All Items take it; Hierarchical and Completed pass
  `segment_color=None` and get a stripe. Where the drawing code does not derive
  its foreground, the colour stays a chip/stripe/icon accent. This replaced a
  blanket ban on full-row fills on 2026-11-11: the ban was guarding against a
  saturated fill under theme-coloured text, and deriving the foreground is what
  actually removes that risk.
- A **priority level** colours one cell, not the row. `priority_levels.row_fill`
  used to take it as a third branch, after the segment colour and the completed
  tint, so a critical item was green across its whole width. Since 2026-11-11 it
  is the background of the Priority cell alone -- `priority_levels.level_cell_fill`
  and `fill_for_level`, which derive the cell's text with `pick_text_color` under
  the same 4.5:1 bar as a row fill. The red that cell used to take,
  `palette["danger"]`, was reachable from no setting and is gone from all five
  list screens; `tests/test_priority_level_colors.py::test_pccm5_no_row_builder_reaches_for_the_danger_palette`
  keeps it gone. A critical I/U factor chip takes the same colour.

## Refactor policy
- No new hard-coded colors in widgets (hex or named colors) except:
  - data-driven segment colors
  - very rare one-off brand assets (must be centralized)
- Replace existing hard-coded fg_color/hover_color/text_color with:
  - theme defaults OR
  - a small semantic style helper -- `src/getmoredone/theme.py`

## Definition of done
1) Theme can be switched via Settings screen (and persists).
2) Sidebar buttons no longer hard-code greens/teals; they follow theme.
3) Row selection highlight is subtle (not a saturated full-row fill).
4) Timer/Edit/Push button hierarchy is consistent (primary/secondary/ghost).
5) Grep shows near-zero hard-coded color strings in UI code.