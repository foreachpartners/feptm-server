# branch-task — Create feature branch across <project> repos

## Demo packaging caveat

Same as [commit-all.md § Demo packaging caveat](commit-all.md#demo-packaging-caveat): the single-tree packaging means there is currently one git repo. In real-world multi-repo deployment, each `<project>-*` is branched independently. The procedure detects which case applies.

## Usage

```
/branch-task                              # auto-derive branch name from active WF-*
/branch-task <branch-name>                # explicit branch name
/branch-task --stash <branch-name>        # stash uncommitted changes first
/branch-task WF-N <branch-name>           # pin to a specific WF
```

## Step 1 — Determine branch name

### Mode A: Active WF-* (no explicit name given)

Locate the active workflow:

```bash
ls ../<analysis-repo>/workflows/WF-*-*/session.yaml 2>/dev/null
```

For each found `session.yaml`, check `status` is `context_ready` or `planned`. Decision:

| Found | Action |
|-------|--------|
| Exactly 1 | Use it |
| Multiple | List, ask user to pick |
| None | Error: "No active workflow. Provide branch name explicitly: `/branch-task feature/my-branch`" |

Extract branch name from the WF directory name:
- `WF-3-wire-eslint-prettier` → branch `feature/wf-3-wire-eslint-prettier`
- Pattern: `feature/{wf-dir-name-lowercased}`

If `branch:` already exists in `session.yaml`, ask: "Branch `{branch}` already recorded in WF-*. Switch to it instead?" — y → checkout existing; n → STOP.

### Mode B: Explicit branch name

Use the provided name as-is. Skip WF lookup.

## Step 2 — Detect repo layout

Same single-vs-multi detection as commit-all:

```bash
TOP_WORKSPACE=$(git rev-parse --show-toplevel)
TOP_BACKEND=$(git -C ../<backend-repo> rev-parse --show-toplevel 2>/dev/null)
```

If equal → operate on the single workspace repo. Otherwise → iterate over each `<project>-{proto,backend,storefront,analysis,workspace}`.

## Step 3 — Confirm and create

Present:

```
Branch: {branch}
Mode: {single-repo demo | multi-repo}
Source branch: {current branch — must be main or already on the target branch}
{If multi-repo: list of N repo paths}
```

Ask: "Create branch `{branch}`{ in all N repos | here}? [--stash: yes/no]"

On confirmation, for each repo:

```bash
git -C <repo_path> stash push -m "branch-task auto-stash"   # only if --stash
git -C <repo_path> checkout main && git -C <repo_path> pull --ff-only
git -C <repo_path> checkout -b <branch>
```

Skip repos already on the target branch. Skip repos not on `main` (unless `--stash` was passed and the user confirmed) — report them.

## Step 4 — Record in WF-* (Mode A only)

If WF-linked, update `WF-*/session.yaml`:

```yaml
branch: feature/wf-N-...
```

Append a line to `WF-*/STATUS.md` noting branch creation.

## Step 5 — Report

```
Branch `feature/wf-N-...` created:
  {repo1}: main → feature/wf-N-...
  {repo2}: main → feature/wf-N-...

Skipped:
  {repo3}: not on main (current: feature/other)

Recorded in WF-N-.../session.yaml.
Next: /plan-task
```

**STOP.** Do not start planning or implementation.

## Safety rules

- Branch source MUST be `main` (or the target branch if already there). Never branch off other feature branches.
- Never force-delete existing branches.
- If a branch with the same name exists in a repo, skip it (do not overwrite).
- Always confirm with user before creating.
