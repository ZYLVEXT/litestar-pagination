---
name: verification-before-completion
description: Use before claiming litestar-pagination work is complete, fixed, passing, built, or ready for release. Run fresh commands that prove each claim and report actual evidence.
---

# Verification Before Completion

## Gate

Before a completion claim:

1. Identify the command or checked requirement that proves it.
2. Run it fresh and inspect the exit code and failures.
3. Report the actual result and any unverified gap.

Do not infer passing behavior from a diff, confidence, cached output, or another agent's report.

| Claim | Required evidence |
| --- | --- |
| Tests and coverage pass | Fresh `just test` output |
| Lint is clean | Fresh `uv run ruff check .` output |
| Format is clean | Fresh `uv run ruff format --check .` output |
| Types pass | Fresh `uv run ty check` output |
| Dependencies are coherent | Fresh `uv run deptry .` output |
| Build succeeds | Fresh `uv build` output and artifact inspection |
| Cursor bug is fixed | Passing regression reproducing the original case |
| Requirements are met | Checked PRD/acceptance list plus relevant tests |

For Python, test, dependency, packaging, executable example, or CI behavior changes run:

```bash
uv run ruff check --fix .
uv run ruff format .
uv run ty check
uv run deptry .
just test
```

For instructions-only Markdown or skills, inspect the content/diff and run only applicable validators. For workflow pins use the commands in `AGENTS.md`.
