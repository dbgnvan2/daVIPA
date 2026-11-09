# Prompt: Test-suite and review-loop remediation

Copy everything below this line into the coding agent.

---

## Context — findings from an external audit (2026-08-20, all measured from git history; do not re-derive, spot-check if you disagree)

- Over the last 100 commits on `main`, tests/ churned 18,876 lines vs 9,548 for src/ (2:1). 18 of 100 commits touched tests with zero src changes; 29 of 100 are sweep-fix commits.
- One batch ran review sweeps to a twelfth pass. Yield did not decay: passes 11 and 12 each still produced 4 findings. Pass 10's fix introduced a high-severity regression that pass 11 caught (commit `2383cbd`). Later-pass findings were meta: defects in guard tests, docstring wording, duplicate pasted functions, message wording.
- ~173 tests (~17% of the suite) across 7 files assert on the repo itself, not the app: `test_ci_contract.py` (78 tests, 1,653 lines on GitHub workflow YAML), `test_release_licensing.py`, `test_packaging_filters.py`, `test_packaging_resources.py`, `test_release_docs.py`, `test_repo_hygiene.py`, `test_traceability_refs.py`. These break on every infra change by design and account for most pure-test-fix commits.
- Commit `3892159` fixed 16 tests that returned a bool instead of asserting; one had been green over a guard dead since a refactor, one opened the production DB on every suite run. 6 test files still assert by grepping source text (`inspect.getsource` / reading `.py` files) — the same pattern that produced the dead guard.

## Task

Do these in order. Commit test changes and src changes separately so the ratio stays visible in `git log --stat`.

### 1. Quarantine the meta-test layer
Add a pytest marker `meta` (register it in `pytest.ini`/`pyproject.toml`) and apply it to all tests in the 7 files listed above. Default `pytest` run must still include them (no silent coverage loss), but `pytest -m "not meta"` must give a fast app-behaviour-only run. Document both invocations in the CLAUDE.md Commands section.

### 2. Eliminate source-grepping assertions
Find every test that asserts by reading source text (`inspect.getsource`, `read_text()`, `open(...*.py`). For each: replace with a behavioural assertion (call the function, assert on the result or on real DB rows in a `tmp_path` database) where feasible. Where a source-text check is the only practical option (e.g. traceability refs), keep it but assert an exact expected count, not a `> N` floor — commit `eac201f` documents why floors hide narrowing.

### 3. Verify no test can touch live data
Audit every test that constructs `DatabaseManager`/`DBManager`: each must receive an explicit `tmp_path` database. Add a conftest guard (fixture or autouse check) that fails any test resolving to the real application-support DB path. Commit `3892159`'s message describes the incident class.

### 4. Vacuous-test scan
Scan all 90 test files for tests that cannot fail: bare `return` of a bool, no `assert` statement in the body, or asserting on a constant. Fix or delete each. Deleting a test that asserts nothing is a valid fix.

## Constraints
- Do not weaken any assertion to make a test pass. If a test fails after your change, state which applies before touching it: (a) code is wrong, (b) behaviour intentionally changed, (c) test was over-specified/vacuous.
- Findings below medium severity that you notice along the way: log to BACKLOG.md, do not fix in this batch.
- Max two review sweep passes over this work. Stop after any pass whose findings are all low severity.

## Verification
- `pytest` fully green; `pytest -m "not meta"` green and measurably faster — record both runtimes in the handoff note.
- Run the suite twice with `pytest -p randomly` (or `--randomly-seed=last` alternate seeds) if pytest-randomly is available in dev deps; any order-dependent failure is a finding.
- Handoff note at `docs/unused-docs/changes/2026-08-20-test-suite-remediation.md` per the template: counts of tests marked `meta`, source-grep assertions replaced vs retained (with reason), vacuous tests fixed vs deleted.
