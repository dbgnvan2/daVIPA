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
pytest -m "not meta"                            # App behaviour only (2432 tests)
pytest -m meta                                  # Repo/infra assertions only (224 tests)
# Both counts measured 2026-11-09 with `-m <marker> --collect-only -q`, whose
# last line prints collected/deselected — re-measure rather than trusting them.
# They had been 1691 and 212, stale by 741 and 12. No test asserts either
# number, which is why they drifted; one that did would go red on every batch.
pytest -v                                       # Verbose
pytest tests/test_vps_integration.py -v        # Single file
pytest --cov=src/getmoredone                   # With coverage

# 22 tests build a real on-screen window and take keyboard focus: the
# geometry checks, and the ones that drive real Tk button events. The count is
# asserted against the suite by tests/test_ci_contract.py, so it cannot drift.
# Skip them while working on the machine. CI never sets this.
GETMOREDONE_NO_MAPPED_WINDOWS=1 pytest

# A full run is ~55s and spawns subprocesses; on a machine someone is using it
# is felt. Prefer the files a change touches, and let CI run the whole suite.
nice -n 19 pytest tests/test_<touched>.py -q

# Create demo data
python tools/create_demo_data.py
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

**Rules — enforce these when writing or reviewing UI code:**
- No hard-coded hex or named colors in widgets. Use theme defaults or semantic tokens from `theme.py`.
- Segment/category colors from DB (`segment_descriptions.color_hex`) are allowed **only** as small accents (chip/stripe/icon), never as full-row fills.
- Only one "primary" color for main action emphasis; success/warning/danger colors are for status only.
- To add a semantic color, centralize it in `theme.py` — do not scatter one-off constants across screen files.

## Working agreements

Work happens on `main`, or on a feature branch merged into it. There are no
per-role branches: the three-agent workflow this section used to describe is
retired — `codex/agent-docs` and `codex/agent-github` never existed as branches,
and `codex/agent-code` was last touched 2026-04-03, 131 commits behind `main`.
See `AGENTS.md` for the full agreements.

**After every batch of work**, write a handoff note at
`docs/changes/<yyyy-mm-dd>-<topic>.md` using template
`.agents/templates/handoff-note.md`. Required fields: summary, files changed,
test/verification status, follow-ups.

If code behavior, UI text, or dependencies changed → docs and the requirements
files must be updated in the same change. Enforced by the docs sync gate
(`.github/workflows/agent-docs-gate.yml`), which treats both `requirements.txt`
and `requirements-dev.txt` as dependency files.

### One build batch at a time

**Only one session builds in this checkout at a time.** A working tree has one
git index, so every concurrent writer races on the same one, whatever the
sessions are to each other — siblings, children of one task, or unrelated. This
is not a rule about tidiness; it is the shape of the tool.

On 2026-11-08 four batches built here at once (WTP, PLC, CE, UPD-M6). What it
cost, measured rather than feared:

- **A commit swept another session's work.** `869cbd6` carried an uncommitted
  `_settings_stub` addition to `tests/test_ape_week_actions.py` that belonged
  to another batch. It is in the repo and no longer shows as pending in the
  tree that wrote it. Two more near-misses followed: six staged PLC source
  files caught before the commit landed, and a `git add` of three shared docs
  that froze a mid-edit snapshot of someone else's prose into the index.
- **Work was deferred that did not need to be.** WTP-M5.2, WTP-M6.4's
  rendering and WTP-M6.5 were filed in `BACKLOG.md` as not built, because
  `screens/weekly_items.py` and `screens/week_actions.py` carried 327
  uncommitted lines from another batch. They were built an hour later when that
  session committed. The spec, the backlog and the handoff note all had to be
  rewritten.
- **The suite could not be run.** Not once all day, because the files kept
  moving underneath it.

Nine files took two or three of those four batches: `BACKLOG.md`,
`docs/DOCUMENTATION_INDEX.md`, `docs/USER_GUIDE.md`, `screens/weekly_items.py`,
`screens/week_actions.py`, `screens/chip_table.py`,
`tests/test_unified_panel_design.py`, `app_settings.py` and `NOTES.md`. That is
not bad luck: the screens share `chip_table.py` and `theme.py`, and every batch
appends to the same three documents, so two UI batches will nearly always
overlap.

So:

- **Finish a batch before starting the next** — `/csdp`, then pushed. This is
  what the working process at the top of `~/.claude/CLAUDE.md` already
  prescribes; the four-at-once day broke it.
- **A session that runs alongside a build is read-only.** Cold review passes,
  "where is X done" investigations, drafting a spec into a new file of its own.
  It commits nothing and stages nothing, so sharing the checkout is safe.
- **No second build — not in a worktree either.** Two concurrent builds in two
  worktrees used to be allowed here, with their file sets checked for overlap
  before either started. Withdrawn 2026-11-08; see "Why the worktree exception
  was withdrawn" below for what it cost.
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

### Why the worktree exception was withdrawn (2026-11-08)

Worktrees did fix what they were adopted for. Each session got its own index,
and after the move to them no commit carried another session's work. What they
did not fix is the thing that actually cost the most: **work that is finished
and not on `main`.**

Measured at the end of 2026-11-08, after the day's batches were pushed
(`7469fc4..b6d6ddf`, CI run 42550648188). The measurement is left as it was
taken; where an item has since been resolved, that is marked in it rather than
edited out, because the argument is about what the day cost, not about the
current state of those branches:

- `main` was red on 20 tests. **Eight passed** on
  `refs/heads/claude/plan-day-range-pdm13`, a branch of 28 commits that was
  never merged. Run at that tip in a separate worktree, all eight pass; on
  `main`, all eight fail. `main` had been given the batch's *tests* — committed
  from the shared checkout — while the work they were written against went on
  in the worktree.
  **Corrected since, and this is the important one:** that was read as "the
  fix is on the branch, merge it", and it was wrong. The PDT batch measured
  `main` at `4ca7116` and found the implementation already there and green at
  both layers; the eight tests passed on the branch because they reached their
  subject through a mechanism — a drop writing the day's hours — that PD-M14
  then withdrew on purpose, and that caused both of the faults the user
  reported. **The branch must not be merged.** The eight were brought up to the
  surviving design instead (`a19a38a`), which is repo test rule case (b).
  `docs/changes/2026-11-08-plan-day-tests-follow-pd-m14.md` has the
  measurement. A test passing on a branch does not establish that the branch
  holds a fix, and this section said it did.
- A ninth, `test_pdm131_a_drop_on_an_end_of_a_non_work_day_extends_the_day`,
  was on `main`, failed there, and existed on no branch. No merge would have
  made it pass. **Resolved since:** `a19a38a` rewrote it to PD-M14's surviving
  design rather than merging the branch, because the mechanism it reached its
  subject through — a drop moving `bounds.day_start` — is what PD-M14.1
  deliberately withdrew. `docs/spec_coverage.md` records PDT-M2.1 against it as
  `done`. It was the clearest case for the point this section makes: a test red
  on `main` for want of a branch, which turned out not to need the branch at
  all.
- `refs/heads/claude/elegant-neumann-ab55c9` held UPD-F1 in three commits —
  the `AppSettings.save()` fix that `NOTES.md` was still recording as "not
  built". It was built, in a worktree, and was not on `main` either.
  **Merged since**, at `2fac9b3`; `git merge-base --is-ancestor
  refs/heads/claude/elegant-neumann-ab55c9 main` succeeds. Twelve places
  across seven documents were still recording the defect as live after it was
  fixed, and it took ten review passes to find them all — the same cost this
  section is about, arriving as stale prose rather than as a red test.

So the failure mode moved rather than disappeared: from one index being raced
by four writers, to four branches each holding a piece, with `main` holding the
tests for work it does not contain. That is worse than a conflict, because a
conflict announces itself at the moment of merging, while a test red on `main`
for want of a branch nobody remembers looks exactly like a bug.

**One batch at a time, with no exception.** Finish it, sweep it, push it, and
start the next only then. A batch that must wait costs hours; this day cost two
orphaned branches, nine red tests with their fix on the wrong side of a merge,
and a suite too red to read.

## Review sweeps

A sweep is a review pass over a batch before it is pushed. The rules exist
because passes are not free: every fix is new unreviewed surface, and a fix
pass has been measured introducing defects at roughly the rate it removes them.

**The pass that matters is a cold one, not an extra warm one.** A warm pass is
run by the context that wrote the code and inherits its blind spots — it runs
out of new assumptions to question long before it runs out of defects. A cold
pass gets the diff and the range and none of the narrative.

The budget:

- **At most 2 warm passes per batch.** Beyond two they converge on the
  reviewer's blind spots, not on correctness, and the falling finding count
  reads as progress while it is measuring exhaustion.
- **At least 1 cold pass, always** — not as a third warm pass, and not only
  when a batch "feels risky". This is the requirement, not the optional extra.
- **A further pass only if the previous one produced a high-severity finding.**
  Make it cold too, and prefer a *different failure family* (correctness, UI
  contract, test quality) over repeating the same sweep.
- **Stop when a pass yields no finding of medium or higher severity.**
- **Every finding gets a severity before any fix is written.** Below-medium
  findings go to `BACKLOG.md`; they are not fixed in-loop, because a cosmetic
  fix buys none of the safety it costs.
- **Every in-loop fix is itself in scope for the next pass.** The fix commit is
  the least-reviewed code in any change — written last, fastest, and in the
  most anchored state.

Evidence for the shape of this, both directions, in
`~/.claude/standards/learnings.md` P26:

- One batch ran to **twelve** warm passes. Passes 11 and 12 still produced four
  findings each, but they were meta — guard tests, docstring wording, message
  phrasing. Pass 10's own fix caused a high-severity regression (`2383cbd`).
- A later batch capped warm passes and ran cold ones instead. Round 3 found a
  guard that had been made *worse* by a previous fix; round 4 found a status
  `print` inside a credential `try` that discarded a valid token on a failed
  stdout write — user-facing, every launch. Both were found cold. Neither would
  have been caught by more warm passes, and a warm-only budget of two would
  have shipped the second.

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
| `daVIPA_MasterSpec_SQLite_v1.md` | Complete technical spec |
| `docs/USER_GUIDE.md` | User documentation |
| `BACKLOG.md` | Development priorities |
| `NOTES.md` | Recent changes and known issues |
| `.agents/templates/handoff-note.md` | Handoff note template |
