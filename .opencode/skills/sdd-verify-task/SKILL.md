---
name: sdd-verify-task
description: Run SDD verification checks at init/implement/finalize phases
---

# sdd-verify-task — SDD Verification Gate

Adapted from `feptm-analysis/docs/skills/verify-task.md`. Runs verification checks at init/implement/finalize phases.

## Prerequisites

- Working directory: `feptm-workspace/`
- CLI tool: `./scripts/sdd-cli.sh`

## Phases

| Phase | Purpose | Checks |
|-------|---------|--------|
| `init` | Snapshot pre-existing findings | AR audit + orphan scan → `baseline.yaml` |
| `implement` | Periodic gate during implementation | typecheck + AR audit delta + task-diff |
| `finalize` | Lock-down before merge | typecheck + AR audit delta + task-diff + traceability orphan delta |

## Usage

### Phase 1: init (once per workflow)

```bash
cd feptm-workspace && ./scripts/sdd-cli.sh verify --wf-dir feptm-analysis/workflows/WF-N-slug --phase init
```

Writes `baseline.yaml`. Commit this alongside `session.yaml`.

### Phase 2: implement (during development)

```bash
cd feptm-workspace && ./scripts/sdd-cli.sh verify --wf-dir feptm-analysis/workflows/WF-N-slug --phase implement --mode fast
```

`--mode fast` skips typecheck (for quick iteration). `--mode full` runs everything.

### Phase 3: finalize (pre-commit)

```bash
cd feptm-workspace && ./scripts/sdd-cli.sh verify --wf-dir feptm-analysis/workflows/WF-N-slug --phase finalize --mode full
```

Adds traceability orphan delta on top of implement checks.

Exit 0 = pass; exit 2 = at least one check failed.

## Inspecting failures

Failures print as:
```
NEW <severity> [<repo>] <check>: <message>
ORPHAN <kind> <name>
```

Resolve by fixing code or updating `audit-exceptions.yaml` (justified entry per AR-REVIEW-004).
