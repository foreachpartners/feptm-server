---
name: sdd-implement-task
description: Execute SDD implementation tasks in order with verification
---

# sdd-implement-task — Execute SDD Implementation Plan

Adapted from `feptm-analysis/docs/skills/implement-task.md`. Reads plan and tasks, executes pending tasks in order, verifies each task.

## Prerequisites

- Working directory: `feptm-workspace/`
- CLI tool: `./scripts/sdd-cli.sh`
- Workflow with `status: planned` or `status: implementing`

## Procedure

### Step 1: Find active workflow

```bash
cd feptm-workspace && ls ../feptm-analysis/workflows/WF-*-*/session.yaml 2>/dev/null
```

Check `status` is `planned` or `implementing`. Handle edge cases:
- If `context_ready` + `plan.md` exists but `tasks.md` missing → auto-generate `tasks.md` first (plan-task Step 7)
- If `context_ready` + no plan → error

### Step 2: Generate session ID

```bash
echo "SID-$(date +%s)-$(uuidgen 2>/dev/null | head -c8 || echo $(shuf -i 1000-9999 -n1))"
```

Write to `WF-*/session.yaml` → `sessions.implement`.

### Step 3: Load plan and find next task

Read from WF-* directory:
1. `session.yaml` — FR IDs, repos, ceremony
2. `plan.md` — technical plan
3. `tasks.md` — task table
4. `context.md` — full context

Find first task with `Status: pending`. Present:
```
Workflow: WF-{ID}-{slug}
Tasks: {done}/{total} done, next: T-{NN} — {description}
```

### Step 4: Execute tasks

For each pending task (in order):

#### 4a. Mark in_progress

Update `tasks.md`: change status to `in_progress`, set `Completed` timestamp (`YYYY-MM-DDTHH:MM`).
Update `session.yaml`: `status: implementing`.

#### 4b. Implement

Read the relevant sections from `plan.md` and `context.md`. Execute the task:
- Edit files as described in the plan
- Add `@req FR-*` annotations per AR-LINEAGE-001
- Run `make typecheck` after Python changes
- Follow existing code conventions in each file

#### 4c. Verify — MANDATORY

```bash
cd feptm-workspace && ./scripts/sdd-cli.sh verify --wf-dir <wf_dir_absolute> --phase implement
```

Exit 0 → mark task `done`. Exit 2 → attempt fix once, re-run verify. If exit 2 again → mark task `blocked` with failure reason.

#### 4d. Update progress

Update `tasks.md` and `STATUS.md`.

### Step 5: Final verification

After all tasks processed:

```bash
cd feptm-workspace && ./scripts/sdd-cli.sh verify --wf-dir <wf_dir_absolute> --phase finalize
```

### Step 6: Report

```
Implementation: {done}/{total} tasks done
Blocked: {blocked} tasks (if any)
Session: {SID}

Done tasks: T-01, T-02, ...
Blocked tasks: T-05 — {reason}

Next: run sdd-finalize-task
```

**STOP.** Do not auto-commit. If any task is `blocked`, report and wait.
