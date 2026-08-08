# Workspace Audit — Run Checks and Evaluate Compliance

Tool: `./scripts/sdd-cli.sh audit --files <path>` (Python CLI).

Run audit checks on specified repos, produce structured report.

## Step 1 — Parse Input

Parse user request. Extract:

- **repos**: which repositories to audit. If unspecified → all repos.
- **mode**: `fast` (default) or `full`. Fast skips cargo/heavy command checks. Full runs everything.

Shorthands:
- "all services" → audit each service-type repo
- "all gateways" → audit each gateway-type repo
- Repo short names: "catalog-service", "gateway", "proto", etc.

To discover repos, run:
```
./scripts/sdd-cli.sh context --list-names
```

## Step 2 — Run Audit

For each repo:

1. Pick any file inside the repo (e.g., `Cargo.toml`, `repo-spec.yaml`, or `README.md`).
2. Run the audit in terminal:
   ```
   ./scripts/sdd-cli.sh audit --files <repo-path>/<file> --mode fast
   ```
   Or for full audit:
   ```
   ./scripts/sdd-cli.sh audit --files <repo-path>/<file> --mode full
   ```
3. Capture full output. Lines starting with `ERR:` are blocking violations. Lines starting with `WARN:` are non-blocking.
4. If output has no ERR/WARN lines → repo PASSes.

All checks are Python-based declarative checks defined in AR spec YAML files (`checks:` field). No bash scripts are used.

If auditing multiple repos, run each separately.

## Step 3 — Return Report

For each repo, produce:

```
## <repo-name> (<type>) — PASS | WARN | FAIL

### ERR (blocking)
- [check-name] message — AR-SPEC-ID

### WARN (non-blocking)
- [check-name] message — AR-SPEC-ID

### Summary
N ERR, M WARN
```

If multiple repos audited, end with summary table:

```
| Repo | Type | ERR | WARN | Status |
|------|------|-----|------|--------|
| catalog-service | service | 2 | 1 | FAIL |
| gateway | gateway | 0 | 3 | WARN |
```

## Constraints

- DO NOT modify any files. This skill is read-only.
- DO NOT run commands other than `sdd-cli audit`.
- DO NOT invent findings. Report only what the audit script outputs.
- If a repo directory does not exist, report it and skip.
