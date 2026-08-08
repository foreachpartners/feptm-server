# sdd-plan-task — Create SDD Technical Plan

Adapted from `feptm-analysis/docs/skills/plan-task.md`. Reads workflow context, drafts a technical plan, persists `plan.md`, and hard-stops for user review.

## Prerequisites

- Working directory: `feptm-workspace/`
- CLI tool: `./scripts/sdd-cli.sh`
- An active workflow with `status: context_ready`

## Procedure

### Step 1: Find active workflow

```bash
cd feptm-workspace && ls ../feptm-analysis/workflows/WF-*-*/session.yaml 2>/dev/null
```

For each found `session.yaml`, read it and check `status` is `context_ready`.

| Found | Action |
|-------|--------|
| Exactly 1 | Use it |
| Multiple | List all, ask user to pick |
| None | Error: "No active workflow. Run sdd-init-task first." |

### Step 2: Generate session ID

```bash
echo "SID-$(date +%s)-$(uuidgen 2>/dev/null | head -c8 || echo $(shuf -i 1000-9999 -n1))"
```

Write this to `WF-*/session.yaml` → `sessions.plan`.

### Step 3: Load context

Read from the WF-* directory:
1. `session.yaml` — FR IDs, repos, ceremony level
2. `context.md` — full SDD context

Present summary:
```
Workflow: WF-{ID}-{slug} ({ceremony} ceremony)
FRs: {fr_ids}
Repos: {repos}
```

### Step 4: Baseline audit review

Read `WF-*/baseline.yaml`. Present summary of pre-existing findings per repo. If violations exist, ask user whether to:
1. **Fix all** — add remediation tasks for all ERR + WARN
2. **Fix ERR only** — fix errors, ignore warnings
3. **Ignore** — enforce zero new violations only

Record decision in `WF-*/session.yaml` as `baseline_policy: fix_all | fix_err | ignore`.

### Step 5: Draft technical plan

Draft `plan.md` covering:

- Architecture Overview (affected repos and data flow)
- REST API / OpenAPI schema changes (endpoints, status codes)
- Storage changes
- Implementation details (handler logic, config, error handling, mappers)
- Security considerations
- Config changes (prefix: `FEPTM_FEPTM_SERVER__`)

Reference specific files with paths throughout.

### Step 6: Persist and HARD STOP

Write `WF-*/plan.md`. Then output:

> Plan written to `WF-*/plan.md`. Open it in your IDE — edit anything, save the file. When done, reply "ok" and I will re-read the plan, generate `tasks.md`, and update status.

**STOP.** Do not proceed until the user explicitly approves.

### Step 7: After user approval — generate tasks.md

Re-read `WF-*/plan.md` (user may have edited it). Generate `WF-*/tasks.md` with ordered tasks:

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | API: ... | FR-ID | — | pending | |

Task ordering: contract → codegen → service → handler → tests → traceability.

The LAST task must be a full audit: `Audit: full repo audit — zero ERR, zero WARN in touched files`.

Update `WF-*/session.yaml`: set `status: planned`.
Update `WF-*/STATUS.md`: append plan summary.

Report:
```
Plan written: WF-*/plan.md
Tasks: {N} items in WF-*/tasks.md
Session: {SID}
Next: run sdd-implement-task
```

**CRITICAL:** Do not edit any file outside the WF-* directory in this phase. Do not run build commands. Code editing is exclusively the responsibility of `sdd-implement-task`.
