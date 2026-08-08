---
name: sdd-finalize-task
description: Prepare final commit with verification and archiving
---

# sdd-finalize-task — Prepare Final Commit

Adapted from `feptm-analysis/docs/skills/finalize-task.md`. Runs final verification, archives plan/tasks, generates commit message.

## Prerequisites

- Working directory: `feptm-workspace/`
- CLI tool: `./scripts/sdd-cli.sh`
- Workflow with `status: implementing` or `status: done`

## Procedure

### Step 1: Find active workflow

```bash
cd feptm-workspace && ls ../feptm-analysis/workflows/WF-*-*/session.yaml 2>/dev/null
```

Read each, check `status` is `implementing` or `done`.

### Step 2: Generate session ID

```bash
echo "SID-$(date +%s)-$(uuidgen 2>/dev/null | head -c8 || echo $(shuf -i 1000-9999 -n1))"
```

Write to `WF-*/session.yaml` → `sessions.finalize`.

### Step 3: Collect changes

Read `session.yaml` — FR IDs, repos. Read `tasks.md` — verify all tasks `done` or `blocked`.

Collect modified files per repo:

```bash
cd <repo_path> && git diff --name-only HEAD
cd <repo_path> && git diff --name-only --cached HEAD
```

### Step 4: Verification gate — BLOCKING

```bash
cd feptm-workspace && ./scripts/sdd-cli.sh verify --wf-dir <wf_dir_absolute> --phase finalize
```

If exit code 2 → **HARD STOP.** Report failures. Do NOT archive. Do NOT generate commit message.

```
## VERIFICATION FAILED — BLOCKING

WF-{ID}-{slug}: verification gate did not pass (exit code 2)
Failures:
- {list each failure}
Action required: fix failures and re-run sdd-finalize-task.
```

### Step 5: Archive (only if verification passed)

1. Create archive dir: `mkdir -p <wf_dir>/archive`
2. Determine sequence number from existing `plan-*.md` files
3. Move active artifacts:
   ```bash
   mv <wf_dir>/plan.md <wf_dir>/archive/plan-NNN.md
   mv <wf_dir>/tasks.md <wf_dir>/archive/tasks-NNN.md
   ```
4. Append row to `STATUS.md` History table

### Step 6: Generate commit message

Format: `WF-{ID}: {summary} [{FR-IDs}]`

Example: `WF-3: implement GET /me endpoint — typed DTOs, error handling, @req [FR-AUTH-006]`

### Step 7: Present dry-run

Show `git status --short` per repo. Present:

```
WF-{ID}-{slug} — ready to commit

Commit: WF-{ID}: {summary} [{FR-IDs}]
Session: {SID}
Verification: sdd-cli verify --phase finalize ✓
```

**STOP.** Do NOT commit. User decides when and how to commit.
