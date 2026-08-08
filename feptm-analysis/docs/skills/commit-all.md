# commit-all — Commit and push across <project> repos

## Demo packaging caveat

In production deployment each `<project>-*` folder is its own GitHub repository. The current single-tree packaging at `~/projects/rezvov/<project>/` collapses them into one git repo (see [`../../README.md`](../../README.md) and `<workspace-repo>/CLAUDE.md`). That means:

- **For the demo as currently packaged**: there is exactly one git repo. `/commit-all` reduces to `git add` + `git commit` + `git push` from the workspace top-level.
- **For real-world multi-repo deployment**: each `<project>-*` is committed independently, but the commit messages share the same FR-* suffix when the work spans repos.

The procedure below describes the demo case; multi-repo logic kicks in only if `git -C ../<backend-repo> rev-parse --show-toplevel` returns a different toplevel than the workspace's.

## Step 1 — Detect repo layout

```bash
TOP_WORKSPACE=$(git rev-parse --show-toplevel)
TOP_BACKEND=$(git -C ../<backend-repo> rev-parse --show-toplevel 2>/dev/null)
```

- If `TOP_WORKSPACE == TOP_BACKEND` → **single-repo demo mode**. Operate on this one repo.
- Otherwise → **multi-repo mode**. Operate on each `<project>-{proto,backend,storefront,analysis,workspace}` independently.

## Step 2 — Read active workflow (for FR suffix)

If a `<analysis-repo>/workflows/WF-*-*/session.yaml` has `status: implementing` or `status: done`, extract:

- `fr_ids` — the FR-* IDs to append as `[FR-X FR-Y]` suffix to the commit message
- `repos` — the repos this workflow touches (multi-repo mode filters by this)

If no active WF-* → no FR suffix; commit message stands alone.

## Step 3 — Show changes and draft message

In **single-repo demo mode**:

```bash
git status --short
git diff --stat HEAD
```

In **multi-repo mode**, repeat per repo in `repos` (or all `<project>-*` if no WF):

```bash
git -C <repo_path> status --short
git -C <repo_path> diff --stat HEAD
```

Draft a concise commit message per repo:

- Subject summarizes the **why**, not the diff. Imperative voice. Under 70 chars.
- If active WF-* → append ` [FR-X FR-Y]`.
- Body (optional) lists motivation, not file list. `git diff --stat` is the file list; do not duplicate it.

Present drafts to the user as a table:

```
| Repo | Branch | Files | Proposed message |
|------|--------|-------|------------------|
| <backend-repo> | feature/wf-N-... | 12 | WF-N: introduce Repository pattern [FR-CART-001] |
```

## Step 4 — Confirm

Ask the user: "Commit all? Or edit messages first?" Wait for explicit approval. The user may:

- Approve all → proceed to Step 5
- Edit a message → re-present
- Skip a repo → drop from list
- Abort → stop

## Step 5 — Commit and push

For each approved repo:

```bash
git -C <repo_path> add <specific files>      # never `git add -A` — risks staging secrets / build artifacts
git -C <repo_path> commit -m "<approved message>"
git -C <repo_path> push
```

In single-repo demo mode `<repo_path>` is `.`.

Refuse to commit on protected branches: `main`. (No staging branch in <project>.) If the current branch is `main`, abort and tell the user to create a feature branch first via `/branch-task`.

## Step 6 — Report

```
Committed and pushed:
  <repo>: <short_hash> "<message>"
```

If any repo failed (e.g., pre-commit hook), continue with remaining repos and surface failures at the end.

## Safety rules

- **Never** push to `main`.
- **Never** use `git push --force` without explicit user instruction; never to `main` even with instruction.
- **Never** skip pre-commit hooks (`--no-verify`) unless user explicitly asks.
- **Never** stage with `git add -A` / `git add .` — name files explicitly to avoid secrets / generated artifacts.
- Always show diff and get user confirmation before committing.
