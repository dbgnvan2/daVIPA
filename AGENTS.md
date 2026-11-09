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
→ One build batch at a time* and *Why the worktree exception was withdrawn*.

## Required handoff artifact

Every batch of work writes a handoff note at:
- `docs/changes/<yyyy-mm-dd>-<topic>.md`

Use template:
- `.agents/templates/handoff-note.md`

Minimum fields:
- Summary of change
- Files changed
- Test/verification status
- Follow-ups for the next session

## Docs sync

If code behaviour, UI text, CLI flags, or dependencies changed, docs and the
requirements files must be updated in the same change. Enforced by
`tests/test_docs_sync_rule.py`, which asserts
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
- Segment/category colors from data (e.g., segment_descriptions.color_hex) are allowed ONLY for small accents (chip/stripe/icon), not full-row fills.

## Refactor policy
- No new hard-coded colors in widgets (hex or named colors) except:
  - data-driven segment colors
  - very rare one-off brand assets (must be centralized)
- Replace existing hard-coded fg_color/hover_color/text_color with:
  - theme defaults OR
  - a small semantic style helper (e.g., ui/theme_tokens.py)

## Definition of done
1) Theme can be switched via Settings screen (and persists).
2) Sidebar buttons no longer hard-code greens/teals; they follow theme.
3) Row selection highlight is subtle (not a saturated full-row fill).
4) Timer/Edit/Push button hierarchy is consistent (primary/secondary/ghost).
5) Grep shows near-zero hard-coded color strings in UI code.