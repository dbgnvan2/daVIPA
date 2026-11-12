# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run application (recommended — auto-creates venv, installs deps, launches app)
./start.sh          # Linux/Mac
start.bat           # Windows

# Manual run
python run.py

# Tests
pytest                                          # All tests
pytest -m "not meta"                            # App behaviour only (2439 tests)
pytest -m meta                                  # Repo/infra assertions only (231 tests)
# Counts measured 2026-11-09 and asserted by nothing — re-measure with
# `-m <marker> --collect-only -q` rather than trusting them.
pytest -v                                       # Verbose
pytest tests/test_vps_integration.py -v        # Single file
pytest --cov=src/getmoredone                   # With coverage

# 25 tests build a real on-screen window and take keyboard focus: the
# geometry checks, and the ones that drive real Tk button events. The count is
# asserted against the suite by tests/test_ci_contract.py, so it cannot drift.
# Skip them while working on the machine. CI never sets this.
GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest

# A full run is ~55s and spawns subprocesses; on a machine someone is using it
# is felt. Prefer the files a change touches, and let CI run the whole suite.
nice -n 19 pytest tests/test_<touched>.py -q

# Create demo data
python tools/create_demo_data.py

# Regenerate the colour inventory. docs/ui_color_inventory.md is generated,
# and tests/test_color_inventory_sync.py fails while it is stale -- so any
# change that adds or removes a colour literal under src/, themes/ or
# tools/generate_ctk_themes.py needs this run committed with it. Those are the
# whole scan (CIV-A1, 2026-11-11), so an edit to a test or a document no
# longer reddens the suite. Needs ripgrep on PATH.
./venv/bin/python tools/color_audit.py
```

## Architecture

**daVIPA** is a Python desktop task management app using CustomTkinter + SQLite.

### Layered structure

- **GUI** — `src/getmoredone/screens/` — 50+ CustomTkinter screen modules
- **Business logic** — `db_manager.py` (primary CRUD + logic hub) + `db_manager_project_boards.py` (split-off project board logic)
- **Data models** — `models.py` — dataclasses: `ActionItem`, `Contact`, `WorkLog`, `TimeBlock`, etc.
- **Database** — `database.py` (schema init + migrations) + SQLite at:
  - macOS: `~/Library/Application Support/GetMoreDone/getmoredone.db`
  - Windows: `%APPDATA%/GetMoreDone/getmoredone.db`
- **Utilities** — `theme.py`, `paths.py`, `validation.py`, `date_utils.py`, `color_contrast.py`, `utils/`

### Entry point

`run.py` → `getmoredone.app.daVIPAApp` → `AppSettings` loaded first (theme applied before UI) → sidebar drives navigation between 13 screens.

### Key data relationships

- `ActionItem` → `Contact` (who field), `ActionItem` (parent_id, hierarchical), `AnnualPlanElement`, `ProjectBoard`, `WorkLog`, `ItemLink`, `RescheduleHistory`
- `Contact` → `Defaults` (per-client settings)

### VSP (Vision Strategy Plan) subsystem

Strategic planning hierarchy: vision → annual plans → quarterly → monthly → weekly tactics.

- Managers: `vps_manager.py`, `vps_manager_taxonomy.py`, `vps_manager_planning.py`
- Schema: `vps_schema.py`
- UI: `screens/vps_planning.py`, `screens/vps_editors.py`, `screens/vps_segment_editor.py`, `screens/vision_planning_hub.py`

### Theme system

CustomTkinter JSON themes in `/themes/`. Loaded at startup via `AppSettings` before any widgets are created.

The colour rules are `AGENTS.md`'s *Semantic color rules* and *Refactor
policy* — one primary, status colours for status only, no new hard-coded
colours in widgets, and a data colour as a row fill only where that row's
foreground is derived from it for contrast — and are not restated here.

## Working agreements

Work happens on `main`, or on a feature branch merged into it. There are no
per-role branches; the three-agent workflow this section used to describe is
retired, and `codex/agent-code` is an ancestor of `main` holding no commit it
lacks. See `AGENTS.md` for the full agreements. The measurements behind the
three sections below are filed in
`docs/unused-docs/changes/2026-11-10-claude-md-narrative.md`.

### Records are filed, not tested

**A document is written to help the work, and filed when it is done.** It is
not a thing the work exists to maintain.

- **Write a handoff note only when it carries something a commit message
  cannot**: a measurement behind a decision, follow-ups not already in
  `BACKLOG.md`, a verification status that is not plainly green, or state the
  next session needs. Otherwise the commit message is the record. The template
  is `.agents/templates/handoff-note.md`; a note goes straight to
  `docs/unused-docs/changes/<yyyy-mm-dd>-<topic>.md`.
- **Write an implementation plan as a file only when the batch warrants one** —
  more than about five criteria, user-visible behaviour, or work that outlives
  a session. Planning before code is still required; becoming a file is not.
- **Filed records are `docs/unused-docs/`.** Handoff notes, implementation
  plans, coverage snapshots, dated status reports. They are kept for recovery
  and for history, and **no test reads them**. A record says what was true on
  its date; a pointer in it to something since deleted is history, not a
  defect.
- **`BACKLOG.md` holds open work and nothing else**, and a commit message is a
  subject and about five lines — both `effort-budget.md`. Here: an item that is
  done or moot leaves, with the reason, to `docs/unused-docs/`.
- **No guard reads prose.** **Nothing in this repo asserts on English — not on
  a document, not on a commit message, not on a docstring's wording.** What
  survives is about code, not writing: `tests/test_repo_hygiene.py` (no stray
  scripts, bundled resources tracked and valid),
  `tests/test_traceability_refs.py` (a `Spec:`/`Tests:` pointer in code or in a
  live spec resolves), `tests/test_ci_contract.py` (the workflow's versions and
  secrets, and the mapped-window count stated in the Commands block above).

What is left live under `docs/` is reference material someone reads *before*
working: the user guide, the dated specs, the master spec, the documentation
index. Plus the four at the root — `CLAUDE.md`, `AGENTS.md`, `BACKLOG.md`,
`NOTES.md` — and `docs/spec_coverage.md`, the criteria-to-tests record.

If code behaviour, UI text, or dependencies changed → docs and the
requirements files must be updated in the same change (global rule 13).
`tools/agents/check_docs_sync.py::verdict` is that decision as a pure function
of changed paths, asserted over fixtures by `tests/test_docs_sync_rule.py`, so
it fails before a push. It does not demand a handoff note, and a file under
`docs/unused-docs/` does not count as the documentation change, because filing
history is not keeping a document current. The suite does not diff your branch:
`tests.yml` checks out at depth 1 and has no `origin/main`. To apply the rule
to real changes, run it by hand:
`./venv/bin/python tools/agents/check_docs_sync.py`. A range it cannot read is
reported as *skipped*, not as a pass. Both `requirements.txt` and
`requirements-dev.txt` are dependency files.

The workflow `agent-docs-gate.yml` is **deleted** as of 2026-11-09 (`SAG-A3`).
It triggered on `pull_request` only, which this repo never produces.

### One build batch at a time

**Only one session builds in this checkout at a time.** A working tree has one
git index, so every concurrent writer races on the same one, whatever the
sessions are to each other — siblings, children of one task, or unrelated.
This is not a rule about tidiness; it is the shape of the tool. Four
concurrent batches on 2026-11-08 swept one session's uncommitted work into
another session's commit, deferred three criteria that were not actually
blocked, and left the suite unrunnable for a day.

- **Finish a batch before starting the next** — `/csdp`, then pushed.
- **A session that runs alongside a build is read-only.** Cold review passes,
  "where is X done" investigations, drafting a spec into a new file of its own.
  It commits nothing and stages nothing, so sharing the checkout is safe.
- **No second build — not in a worktree either.** Two concurrent builds in two
  worktrees were allowed here until 2026-11-08, with their file sets checked
  for overlap first. Withdrawn: separate indexes did stop the commit
  collisions, but they left finished work sitting on branches `main` did not
  have, and `main` holding the tests for code it did not contain. A conflict
  announces itself at the moment of merging; a test red on `main` for want of a
  branch nobody remembers looks exactly like a bug. **No exception.**
- **Keep a batch's doc work in its own new files** while the batch runs — its
  spec, its handoff note — and add the `BACKLOG.md`, `docs/USER_GUIDE.md` and
  `docs/DOCUMENTATION_INDEX.md` entries last, after the merge. Those three are
  the chronic conflict surface because every batch writes to the same region of
  each.

**Never stage a file to protect your own committed work.** The index is shared;
staging a file another session is editing freezes its half-finished state where
an index-based `git commit` will pick it up. Commit your own paths explicitly
instead — `git commit -- <paths>`, or a filtered patch applied to a temporary
`GIT_INDEX_FILE` when one file holds two sessions' hunks — and leave the index
as you found it.

## Review sweeps

A sweep is a review pass over a batch before it is pushed. Which tier a change
earns, that below-medium findings are dropped, and when to stop, are
`~/.claude/standards/effort-budget.md` — read on every task, and not restated
here. For this repo: `src/`, a data path, a status machine, an external call or
a scoring function earns the full budget; tests, config or a document alone
earns no sweep at all; mixed, sweep the `src/` half.

Four rules are this repo's own and are not in that standard:

- **At most 2 warm passes per batch.** Beyond two they converge on the
  reviewer's blind spots, not on correctness, and the falling finding count
  reads as progress while it is measuring exhaustion.
- **At least 1 cold pass, always** — not as a third warm pass, and not only
  when a batch "feels risky". This is the requirement, not the optional extra.
- **A further pass only if the previous one produced a high-severity finding.**
  Make it cold too, and prefer a *different failure family* (correctness, UI
  contract, test quality) over repeating the same sweep.
- **Every in-loop fix is itself in scope for the next pass.** The fix commit is
  the least-reviewed code in any change — written last, fastest, and in the
  most anchored state.

Evidence both directions — the batch that ran to twelve warm passes and the one
that capped them and ran cold passes instead — is `learnings.md` P26.

## Test rules

- **Every test must be able to fail.** No returning bools, no assert-free
  bodies. Prove it by mutation — delete or invert the line the test names, run
  it, confirm red, restore — and mutate with the **verbatim** original, never a
  simplified reconstruction.
- **Never modify a test to make it pass** without first stating which applies:
  (a) the code is wrong, (b) the behaviour changed intentionally, (c) the test
  was over-specified or vacuous.
- **Do not assert by grepping source text** unless no behavioural check is
  practical. Where a source-text guard is unavoidable, parse it (walk the AST,
  or anchor the match to a whole line) and assert **exact counts**, never
  `> N` floors — a floor hides the narrowing it was written to catch.
- **Every `DatabaseManager` in a test takes an explicit `tmp_path` database.**
  The default path resolves to the user's real application database, and
  `__init__` runs migrations against it.
- **Commit test changes separately from `src/` changes**, so the ratio stays
  visible in `git log --stat`.

## Global standards

Read the relevant file from `~/.claude/standards/` before starting work:

| Standard | When |
|---|---|
| `file-maintainability.md` | Any new file or significant refactor (replaces the inline policy previously here) |
| `ui-regression.md` | Any change to the 50+ CustomTkinter screens — treat every screen's controls as a contract |
| `security.md` | SQLite parameterised queries, input validation, no secrets in code |
| `learnings.md` | P6 (trust status fields only after verifying the DB row), P8 (dirty-state tests for SQLite reads) |

In tabular/dual-panel UIs, aligned columns are a design goal — matching columns must use consistent widths across rows and paired panels.

## Key files

| File | Purpose |
|---|---|
| `codex.md` | Full file maintainability policy — read before any refactor |
| `AGENTS.md` | Multi-agent workflow rules + theme system spec |
| `GetMoreDone_MasterSpec_SQLite_v1.md` | Complete technical spec |
| `docs/USER_GUIDE.md` | User documentation |
| `BACKLOG.md` | Development priorities |
| `NOTES.md` | Recent changes and known issues |
| `.agents/templates/handoff-note.md` | Handoff note template |
