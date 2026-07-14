---
name: github-actions-pin-refresh
description: "Audit `.github` workflows for remote `uses:` entries pinned to full commit SHAs, resolve the newest intended upstream refs, refresh the pinned SHAs, and update trailing version comments when they change. Use when reviewing stale GitHub Actions pins or normalizing `uses: owner/repo@SHA # vX.Y.Z` lines."
---

# GitHub Actions Pin Refresh

Use this skill when changing `.github/workflows/*.yml` or reusable workflows that pin remote actions by full SHA.

Use AgentMemory for prior CI/release decisions before changing workflow behavior. CodeGraph is usually unnecessary for pin-only edits; use it only if workflow changes require code impact analysis.

## Goal

Keep remote `uses:` lines on full 40-character commit SHAs while moving them to the newest intended upstream version and keeping the trailing `# ...` comment honest.

## Inventory First

Run the bundled check before editing:

```bash
python3 .agents/skills/github-actions-pin-refresh/scripts/list_pinned_actions.py --check
python3 .agents/skills/github-actions-pin-refresh/scripts/list_pinned_actions.py --format json
```

`--check` exits nonzero for a mutable remote GitHub-hosted ref. The inventory command lists existing full-SHA pins like:

```yaml
uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2
```

It intentionally ignores local actions (`./...`) and docker actions.

## Update Workflow

For each unique `owner/repo[/path]` found under `.github/`:

1. Read the current trailing comment, if any.
2. Resolve the target upstream ref:
   - Default: the newest stable release or tag.
   - Ignore prereleases unless the current pin already tracks one or the user explicitly asks for prereleases.
   - If the existing comment is a channel such as `v4`, `v4.1`, `main`, or `master`, preserve that channel unless the user explicitly asks for a cross-channel or cross-major jump.
3. Resolve the exact commit SHA for that ref.
4. Rewrite the YAML to keep full-SHA pinning:
   - `uses: owner/repo[/path]@<40-char-commit-sha> # <comment>`
5. Update the trailing comment when needed:
   - exact-version comments such as `# v6.0.2` should become the new exact tag;
   - channel comments such as `# v6`, `# v6.1`, or `# main` stay channel comments;
   - if comments are used consistently in the file and one pinned action is missing its comment, add the resolved ref comment.
6. If the update crosses a major version, skim upstream release notes or changelog before finalizing and adjust the workflow if required (inputs, permissions, Node/runtime expectations, removed flags).

## Resolve Refs Without Guessing

Prefer GitHub CLI when it is available.

### Latest Stable Release

```bash
gh api repos/{owner}/{repo}/releases/latest
```

Use this when the action publishes stable GitHub releases.

### Exact Tag or Branch Ref

```bash
gh api repos/{owner}/{repo}/git/ref/tags/{tag}
gh api repos/{owner}/{repo}/git/ref/heads/{branch}
```

Annotated tags point to tag objects, not directly to commits. Dereference them:

```bash
gh api repos/{owner}/{repo}/git/tags/{tag_object_sha}
```

Use the nested `object.sha` commit as the final pin when the tag is annotated.

### When `releases/latest` Is Unavailable

```bash
gh api repos/{owner}/{repo}/tags?per_page=100
```

Pick the newest stable semver tag that matches the intended track. Do not upgrade a stable track to a prerelease.

If GitHub CLI is unavailable, fall back to GitHub's web/API surface or `git ls-remote` for exact refs. Still resolve to a commit SHA and keep the workflow pinned to that full SHA.

## Editing Rules

- Never replace a full-SHA pin with a mutable tag or branch.
- Preserve `owner/repo/path` subpaths for nested actions and reusable workflows.
- Keep one upstream ref per action family consistent across the repo unless a workflow intentionally needs a different version.
- Do not invent comments that you cannot justify from the resolved upstream ref.
- If an upstream release changes required permissions or inputs, update the workflow in the same change.
- Keep YAML formatting and indentation stable so the diff is easy to review.

## Verification

- Re-run the bundled `--check` to confirm every remote GitHub-hosted `uses:` line is pinned to a 40-character SHA.
- Review `rg "uses:" .github -n` and the `.github` diff.
- For workflow-only pin refreshes, run the workflow-specific checks from `AGENTS.md`:
  ```bash
  python3 .agents/skills/github-actions-pin-refresh/scripts/list_pinned_actions.py --check
  python3 .agents/skills/github-actions-pin-refresh/scripts/list_pinned_actions.py --format text
  rg "uses:" .github -n
  git diff -- .github
  ```
- If the workflow change modifies job commands, permissions, matrices, release behavior, or anything that changes how the library is built, tested, published, or deployed, also run the relevant targeted project checks. Use the full Python verification block only when the workflow change needs local evidence that the library test/build path still works.
