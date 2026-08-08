# implement-task — Execute SDD Implementation Plan

CLI tool: `./scripts/sdd-cli.sh`
Workflow directory: `<analysis-repo>/workflows/WF-*-*/`


Reads plan.md and tasks.md from the current WF-* directory. Executes pending tasks in order. Updates STATUS.md and tasks.md as work progresses.

### Usage

```
/implement-task                                   # auto-detect WF-* dir
/implement-task WF-2002                           # explicit WF-* dir
/implement-task T-03                              # start from specific task
```

### Step 0: Session tracking

Extract session ID (run ONCE at the start of this phase):

```bash
PROJ_DIR="$HOME/.claude/projects/$(pwd | tr '/' '-')"
CLAUDE_SID=$(stat --format='%W %n' "$PROJ_DIR"/*.jsonl 2>/dev/null \
  | sort -rn | head -1 | awk '{print $2}' | xargs basename 2>/dev/null)
CLAUDE_SID="${CLAUDE_SID%.jsonl}"
echo "Session: $CLAUDE_SID"
```

Include `Session: {CLAUDE_SID}` in the final chat output.

Persist to `WF-*/session.yaml` — add or update `sessions` mapping (write only the `implement` key).

### Step 1: Find WF-* directory

Same as Phase 2 Step 1, but look for `status: planned` or `status: implementing` — with one extra case for the plan-task hard-stop in-between state (see decision table).

Run in terminal:
```
ls ../<analysis-repo>/workflows/WF-*-*/session.yaml 2>/dev/null
```

For each found session.yaml read `status`, and check whether `plan.md` and `tasks.md` exist next to it.

Decision table:

| `status` | `plan.md` | `tasks.md` | Action |
|----------|-----------|------------|--------|
| `planned` or `implementing` | exists | exists | Normal case: use this WF |
| `context_ready` | exists | missing | plan-task Phase 2a hard-stopped without proceeding to Phase 2b. Auto-complete Phase 2b first: re-read `plan.md`, generate `tasks.md`, set `status: planned`, append plan-summary to `STATUS.md`. Then continue with Step 2 of this skill. |
| `context_ready` | missing | — | Error: "No plan. Run /plan-task first." |
| anything else | — | — | Error: "No planned workflow. Run /plan-task first." |

If multiple WF-* candidates match, list them and ask the user to pick.

### Step 2: Load plan and find next task

Read from WF-* directory:

1. `session.yaml` — FR IDs, repos, ceremony
2. `plan.md` — technical plan
3. `tasks.md` — parse the task table
4. `context.md` — full context (for delegation)

Find the first task with `Status: pending`. If an explicit task ID was given (e.g., `T-03`), start from that task.

Present summary:
```
Workflow: WF-{ID}-{slug}
Plan: WF-*/plan.md
Tasks: {done}/{total} done, next: T-{NN} — {description}
```

### Step 3: Execute tasks

For each pending task (in order):

#### 3a. Mark in_progress

Update `tasks.md`: change task status from `pending` to `in_progress`. Set `Completed` column to current timestamp (`YYYY-MM-DDTHH:MM`).
Update `session.yaml`: set `status: implementing` (if not already).

#### 3b. Delegate implementation

Delegate each task to a capable agent or execute directly. The delegation prompt MUST include:
- The specific task description from tasks.md
- The relevant section from plan.md
- The affected repo paths (from session.yaml repos)
- Key context from context.md (proto contracts, handler patterns, entity structure)
- CLAUDE.md reference for project conventions

Example prompt structure:
```
Read CLAUDE.md at {workspace}/CLAUDE.md.

## Task
{task description from tasks.md}

## Plan excerpt
{relevant section from plan.md}

## Context
{relevant sections from context.md — proto, handlers, entity, etc.}

## Repos
{repo paths}

## Constraints
- Follow SDD spec-first principle
- Add @req annotations per AR-LINEAGE-001
- No visual noise: no section dividers (// ====, // ----, // ****), no banner comments
- Logging level: use debug! for high-frequency read endpoints (GET), info! for mutations (POST/PUT/DELETE)
- Keep inline comments consistent with existing style in the same module
- OpenAPI: every operation MUST have x-requirement: FR-*. Schema enum values MUST be verified against proto/service code (not assumed). Schema required/optional MUST match proto message optionality.
- Run cargo check after changes
```

#### 3c. Verify — MANDATORY

After implementation completes, run unified verification in terminal:

```bash
./scripts/sdd-cli.sh verify --wf-dir {wf_dir} --phase implement
```

Runs (in order): cargo check → clippy → test, AR audit delta vs baseline, task-diff verification. Only NEW findings (not in baseline.yaml) block.

If exit code 2 → verification failed. **Do NOT mark task as `done`.** Read output to identify failures.

On first failure — attempt fix:
- **Cargo failure**: re-implement with compilation/lint/test errors provided
- **Audit delta failure**: re-implement with specific new findings provided
- **Task-diff failure**: re-implement with "Task {T-NN} produced no expected changes. File {X} was expected to be modified but is not in git diff."

Re-run verify after fix. If exit code 2 again → **mark task `blocked`** with failure reason. Output:

```text
## TASK BLOCKED — T-{NN}

Verification failed after retry. Task marked as blocked.

Failures:
- {list each failure from verify output}

Blocked tasks: T-{NN}
Action required: user must resolve before continuing.
```

**IMPORTANT**: A task is `done` ONLY when verify exits 0. Never mark a task `done` if verify exits 2.

#### 3d. Update progress

Update `tasks.md`: set task status to `done` (verify exit 0) or `blocked` (verify exit 2). Set `Completed` column to current timestamp (`YYYY-MM-DDTHH:MM`).
Update `STATUS.md`: append progress entry.

#### 3e. Next task

Continue to next `pending` task. Repeat 3a-3d.

Stop conditions:
- All tasks `done` → proceed to Step 4
- A `blocked` task blocks dependent tasks → skip dependents, continue with independent tasks
- User interrupts → stop, preserve current state

### Step 4: Finalize

After all tasks processed:

1. Run full traceability check in terminal:
   ```
   ./scripts/sdd-cli.sh traceability
   ```

2. Update `session.yaml`: set `status: done` (if all tasks done) or `status: implementing` (if blocked tasks remain).

3. Update `STATUS.md`: final status with completed/blocked summary.

### Step 5: Report

```
Implementation: {done}/{total} tasks done
Blocked: {blocked} tasks (if any)
Session: {CLAUDE_SID}
Traceability: {coverage result}

Done tasks: T-01, T-02, T-03, ...
Blocked tasks: T-05 — {reason}

Files to commit:
  WF-* artifacts: plan.md, tasks.md, STATUS.md, session.yaml
  Code changes: {list of modified files in service repos}
```

Next: `/finalize-task` to prepare commit with WF-* artifacts + code changes.

**End of phase:**

- **Standalone `/implement-task`** → STOP. Wait for the user to invoke `/finalize-task` explicitly.
- **Chained from higher-level intent** ("implement X") → proceed directly to `/finalize-task` on the same turn. The verify gate inside finalize will hard-stop if anything is wrong; that's the safety net, not a manual handoff.
- **Any task ended in `blocked`** → STOP regardless of mode. Report the blocker and wait for the user — finalize will fail anyway and re-running from a stale state is wasteful.

---
