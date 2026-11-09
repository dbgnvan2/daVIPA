# Prompt: Update CLAUDE.md and learnings.md from the 2026-08-20 audit

Copy everything below this line into the coding agent.

---

## Context

An external audit of this repo (2026-08-20) found: review sweeps ran to twelve passes without finding-count decay, a pass-10 fix introduced a high-severity regression caught at pass 11 (`2383cbd`), test churn ran 2:1 over src churn across the last 100 commits, 16 tests were incapable of failing (`3892159`, one opened the production DB), and `CLAUDE.md` still documents a three-agent branch workflow the latest handoff note (`docs/changes/2026-08-20-backlog-batch-3.md`) confirms is dormant (`codex/agent-docs` and `codex/agent-github` never existed as branches; `codex/agent-code` last touched 2026-04-03, 131 commits behind).

This is a docs-only task. Do not change src/ or tests/.

## Task 1 — CLAUDE.md

1. **Retire the "Multi-agent workflow" section.** Replace with a short paragraph: work happens on `main` (or feature branches); the handoff-note requirement at `docs/changes/<yyyy-mm-dd>-<topic>.md` and the docs-sync rule (behavior/UI/dependency changes must update docs and requirements in the same PR) are retained. Make the matching correction in `AGENTS.md` or, if that file is now entirely about the dead workflow, replace its contents with a pointer to CLAUDE.md.
2. **Add a "Review sweeps" section** with these rules:
   - Maximum 2 sweep passes per batch; a third only if the previous pass produced a high-severity finding.
   - Stop when a pass yields no finding of medium or higher severity.
   - Every finding gets a severity before any fix. Below-medium findings go to BACKLOG.md, not fixed in-loop.
   - Every in-loop fix is itself in scope for the next pass — this is why the pass cap exists.
3. **Add a "Test rules" subsection** under Architecture or as its own section:
   - Every test must be able to fail: no returning bools, no assert-free bodies. Never modify a test to make it pass without first stating which applies: code wrong / behaviour intentionally changed / test over-specified.
   - No asserting by grepping source text unless no behavioural check is practical; source-text guards must assert exact counts, not `> N` floors.
   - Every `DatabaseManager` in a test takes an explicit `tmp_path` database — never the default path.
   - Commit test changes separately from src changes.
   - Note the `meta` marker and the `pytest -m "not meta"` invocation in the Commands block (add it as pending if the remediation batch has not landed yet).
4. Do not reformat or rewrite unrelated sections.

## Task 2 — ~/.claude/standards/learnings.md

Read the file first and match its existing numbering and entry format (it has entries at least through P8). Append new numbered entries covering, one each:

- **Vacuous tests**: a test that returns a bool or lacks asserts reports green forever; the deletion-protection guard was dead for months behind one (`3892159`). Periodically scan for tests that cannot fail.
- **Default DB paths in tests**: constructing the DB manager without an explicit path resolves to production data and runs migrations against it. Tests must always pass `tmp_path`.
- **Fix passes create defects**: a review-pass fix introduced a high-severity regression (`2383cbd` — pass 10 changed a count's meaning, left the message deriving from the old meaning). Treat every fix commit as new surface for exactly one follow-up pass, then stop; unbounded re-sweeping does not converge.
- **Floor assertions hide narrowing**: `assert len(found) > 20` stayed green while coverage silently dropped 154 → 127 (`eac201f`). Guards over enumerable sets assert exact counts.
- **Source-grep assertions go stale**: asserting a name appears in a function's source breaks silently on refactor (the `vision_count` case in `3892159`). Assert behaviour, not source text.

Where an entry duplicates an existing learning, extend the existing entry instead of adding a new number.

## Verification
- `git diff` shows only CLAUDE.md, AGENTS.md, and the learnings file changed.
- Cited commits (`3892159`, `2383cbd`, `eac201f`) exist and their messages support the claims — check with `git log -1 --format=%b <hash>` before writing.
- Handoff note at `docs/changes/2026-08-20-docs-workflow-update.md`.
