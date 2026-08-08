# create-mr — Open a GitHub pull request

<project> hosts on GitHub (`github.com:<org>/<repo>`); all PR operations use the `gh` CLI. The skill drafts a title + body from commits on the current branch, presents for approval, then opens the PR.

## Usage

```
/create-mr                              # auto-detect repo + branch; target = main
/create-mr --target <branch>            # override target branch
/create-mr --draft                      # open as draft
/create-mr --reviewer <gh-handle>       # set reviewer (can repeat)
/create-mr --assignee <gh-handle>       # set assignee
```

## Step 1 — Validate state

```bash
git rev-parse --abbrev-ref HEAD          # current branch
git status --short                        # working tree must be clean (commit first)
git log origin/main..HEAD --oneline       # commits ahead of main
```

Refuse to proceed if:
- Current branch is `main` → "PRs are opened from feature branches; branch first via `/branch-task`."
- Working tree dirty → "Commit or stash uncommitted changes first."
- Zero commits ahead of `main` → "No commits to open a PR with."

## Step 2 — Push branch (if needed)

```bash
git rev-parse --abbrev-ref @{upstream} 2>/dev/null  # has upstream?
```

If no upstream: `git push -u origin <branch>`. Confirm with user before pushing if branch has uncommitted history (force-push not used).

## Step 3 — Draft title and body

Read commits via `git log origin/main..HEAD --reverse --pretty=format:"%s%n%n%b"`.

**Title** — under 70 chars. Imperative voice. If a single dominant commit, reuse its subject (stripped of trailing FR-* suffix). For multiple commits, summarize the cross-cutting theme.

**Body** template (Markdown):

```markdown
## Summary

- <1–3 bullets, what changed and why>

## Test plan

- [ ] <what you ran or expect reviewers to verify>
- [ ] <e.g., cargo check / cargo test / pnpm build / smoke endpoint>

## Linked workflow

WF-N (if applicable) — list the FR-* IDs covered by this PR.
```

If a WF-*-* is active and tracks the current branch (matches `branch:` in `session.yaml`), include the WF and its FR-* IDs. Otherwise omit the section.

## Step 4 — Present for approval

```
PR Draft
────────
Repo:       <org>/<repo>
Branch:     {branch} → {target} (default: main)
Title:      {generated}
Reviewer:   {handle or "—"}
Assignee:   {handle or "—"}
Draft:      {yes/no}

Body:
{generated body}
```

**STOP.** Wait for the user to approve, edit, or abort. Do not open the PR until explicit confirmation.

## Step 5 — Open PR

```bash
gh pr create \
  --title "<approved-title>" \
  --body "<approved-body>" \
  --base <target> \
  $([ "$DRAFT" = yes ] && echo --draft) \
  $([ -n "$REVIEWER" ] && echo --reviewer "$REVIEWER") \
  $([ -n "$ASSIGNEE" ] && echo --assignee "$ASSIGNEE")
```

`gh` auto-detects the repo from the upstream; no `--repo` needed when run inside the working tree.

## Step 6 — Report

```
PR opened: <url-from-gh-output>
  Branch:   {branch} → {target}
  Reviewer: {handle or "—"}
```

## Constraints

- DO NOT open the PR without user approval of title + body (Step 4).
- DO NOT push to `main` directly; the PR is the only path.
- Default target: `main`. No `dev` / `staging` branch in <project>.
- Default: branch is NOT auto-deleted on merge; reviewer or merger decides.
- If reviewer is not in the repo's collaborator list, the API call will fail — surface the error to the user, do not silently retry.
