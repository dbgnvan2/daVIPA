# Multi-Agent Workflow (Code + Docs + GitHub)

This project includes a starter setup for running three parallel agents with explicit handoffs.

## Agents

- Code Agent: implement features/fixes and tests
- Docs Agent: update requirements, user guide, and docs index
- GitHub Agent: manage PR quality gates, labels, and merges

Role prompts live in:
- `.agents/prompts/code-agent.md`
- `.agents/prompts/docs-agent.md`
- `.agents/prompts/github-agent.md`

## One-time setup

From repo root:

```bash
tools/agents/setup_worktrees.sh ../daVIPA-agents
```

This creates:
- `../daVIPA-agents/code` on `codex/agent-code`
- `../daVIPA-agents/docs` on `codex/agent-docs`
- `../daVIPA-agents/github` on `codex/agent-github`

## Daily usage

1. Run one agent session in each worktree.
2. Keep each role inside its ownership boundaries from `AGENTS.md`.
3. After each meaningful change, create a handoff note in `docs/changes/`.
4. Open/update PR with `.github/pull_request_template.md`.

## Docs gate behavior

The rule is `tools/agents/check_docs_sync.py`, asserted by
`tests/test_docs_sync_rule.py` and so run with the suite on every push. It was
a pull-request workflow, `agent-docs-gate.yml`, until
2026-11-09; that workflow had never run, because this repo opens no pull
requests (`SAG-A3`).

What the suite runs is `verdict`, the decision as a pure function of changed
paths, over fixtures — **it does not diff your branch.** `tests.yml` checks out
at depth 1 and has no `origin/main` to diff against, so a test that asked for
the range would skip on CI. To apply the rule to a real change, run it by
hand:

```bash
./venv/bin/python tools/agents/check_docs_sync.py
```

A range it cannot read is reported as *skipped*, not as a pass. So an
undocumented change does not turn CI red; nothing but that command and the
reviewer catches it.

The rule's verdict is "fail" when:
- code/dependency files changed (`src/`, `tools/`, `tests/`, `requirements.txt`
  or `requirements-dev.txt`), and
- no documentation update is present, or
- no handoff note exists in `docs/changes/`

## Handoff template

Use:
- `.agents/templates/handoff-note.md`

Recommended filename:
- `docs/changes/YYYY-MM-DD-topic.md`
