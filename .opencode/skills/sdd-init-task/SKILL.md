---
name: sdd-init-task
description: Initialize SDD workflow context and capture baseline
---

# sdd-init-task — Initialize SDD Workflow Context

Adapted from `feptm-analysis/docs/skills/init-task.md`. This skill initializes a WF-* workflow directory for the fep-sdd Spec-Driven Development pipeline.

## Prerequisites

- Working directory: `feptm-workspace/`
- CLI tool: `./scripts/sdd-cli.sh`

## Procedure

### Step 1: Determine repos and FRs

Run context overview:

```bash
cd feptm-workspace && ./scripts/sdd-cli.sh context --scope
```

From the output, identify:
- Which repos are affected (minimum set needed)
- Which FR IDs are relevant

If the user didn't specify repos, ask which repos to scope (server, analysis, workspace).

### Step 2: Generate session ID

```bash
echo "SID-$(date +%s)-$(uuidgen 2>/dev/null | head -c8 || echo $(shuf -i 1000-9999 -n1))"
```

Use this as the session identifier. Save it — you'll write it to `session.yaml` in Step 4.

### Step 3: Initialize workflow

Run from `feptm-workspace/`:

```bash
./scripts/sdd-cli.sh init \
  --name <name1> --name <name2> \
  --fr FR-XXX-NNN --fr FR-YYY-MMM \
  --description "<1-2 sentence task description>"
```

`--name` values come from `./scripts/sdd-cli.sh context --list-names`.
`--fr` is required — list all relevant FR IDs.
`--description` is required — used to name the workflow directory.

If the tool reports existing candidates (overlapping active workflows), present them to the user with scores and ask whether to reuse or create new. Then re-run with `--wf <name>` (reuse) or `--wf new` (fresh).

### Step 4: Persist session ID

Read `WF-*/session.yaml` from the output's `wf_dir`. Write the session ID from Step 2 into `sessions.init`.

### Step 5: Baseline audit

```bash
./scripts/sdd-cli.sh verify --wf-dir <absolute_path_to_wf_dir> --phase init
```

This captures pre-existing findings into `baseline.yaml` so later phases only flag new violations.

### Step 6: Summarize

Read `WF-*/context.md` (first 30 lines — completeness table + scope). Present:

```
WF-{ID}-{slug} initialized ({ceremony} ceremony)

| Artifact | Path |
|----------|------|
| Folder | [WF-...](../feptm-analysis/workflows/WF-.../) |
| Context | [context.md](../feptm-analysis/workflows/WF-.../context.md) |
| Session | [session.yaml](../feptm-analysis/workflows/WF-.../session.yaml) |
| Status   | [STATUS.md](../feptm-analysis/workflows/WF-.../STATUS.md) |
| Baseline | [baseline.yaml](../feptm-analysis/workflows/WF-.../baseline.yaml) |

Session: {SID}

Next: run sdd-plan-task
```

**STOP.** Do not proceed to planning.
