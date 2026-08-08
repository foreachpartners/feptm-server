---
name: sdd-branch-task
description: Create feature branch across feptm repos
---

# sdd-branch-task — Create Feature Branch Across Repos

Adapted from `feptm-analysis/docs/skills/branch-task.md`. Creates a feature branch from `main` across feptm repos.

## Prerequisites

- Working directory: `feptm-workspace/`

## Procedure

### Step 1: Determine branch name

Locate active workflow:

```bash
cd feptm-workspace && ls ../feptm-analysis/workflows/WF-*-*/session.yaml 2>/dev/null
```

Check `status` is `context_ready` or `planned`.

| Found | Action |
|-------|--------|
| Exactly 1 | Extract branch name: `feature/{wf-dir-name-lowercased}` |
| Multiple | List, ask user to pick |
| None | Ask user for explicit branch name |

If `branch:` already exists in `session.yaml`, ask: "Branch already recorded. Switch to it?"

### Step 2: Detect repo layout

```bash
TOP_WORKSPACE=$(git rev-parse --show-toplevel)
TOP_SERVER=$(git -C ../feptm-server rev-parse --show-toplevel 2>/dev/null)
```

If equal → single-repo mode. Otherwise → iterate over each `feptm-*`.

### Step 3: Confirm and create

Present:
```
Branch: {branch}
Mode: {single-repo | multi-repo}
Source branch: main
```

Ask to confirm. On confirmation, for each repo:

```bash
git -C <repo_path> checkout main && git -C <repo_path> pull --ff-only
git -C <repo_path> checkout -b <branch>
```

Skip repos already on target branch. Skip repos not on `main`.

Safety rules:
- Source must be `main` (or target branch if already there)
- Never force-delete existing branches
- If branch with same name exists, skip it

### Step 4: Record branch

Update `WF-*/session.yaml`:
```yaml
branch: feature/wf-N-...
```

Append to `WF-*/STATUS.md`.

### Step 5: Report

```
Branch `feature/wf-N-...` created:
  {repo1}: main → feature/wf-N-...
Next: run sdd-plan-task
```
