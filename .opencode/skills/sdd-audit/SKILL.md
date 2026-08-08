---
name: sdd-audit
description: Run AR-spec audit checks on specified repos
---

# sdd-audit — Workspace Audit

Adapted from `feptm-analysis/docs/skills/audit.md`. Runs AR-spec audit checks on specified repos.

## Prerequisites

- Working directory: `feptm-workspace/`
- CLI tool: `./scripts/sdd-cli.sh`

## Procedure

### Step 1: Parse input

Determine which repos to audit. If unspecified → all repos. Determine mode: `fast` (default, no typecheck) or `full` (includes typecheck/lint/test).

Repo short names: `server`, `analysis`, `workspace` (from `./scripts/sdd-cli.sh context --list-names`).

### Step 2: Run audit

For each repo, pick any file inside it and run:

```bash
cd feptm-workspace && ./scripts/sdd-cli.sh audit --files ../feptm-{name}/{file} --mode fast
```

For full mode:
```bash
cd feptm-workspace && ./scripts/sdd-cli.sh audit --files ../feptm-{name}/{file} --mode full
```

### Step 3: Report

For each repo:
```
## {repo-name} ({type}) — PASS | WARN | FAIL

### ERR (blocking)
- [check-name] message — AR-SPEC-ID

### WARN (non-blocking)
- [check-name] message — AR-SPEC-ID

Summary: N ERR, M WARN
```

Multi-repo audit ends with summary table:
```
| Repo | Role | ERR | WARN | Status |
|------|------|-----|------|--------|
| server | service | 2 | 1 | FAIL |
```

## Constraints

- Read-only — do not modify any files
- Only run `sdd-cli audit` — no other commands
- Report only what the script outputs — do not invent findings
