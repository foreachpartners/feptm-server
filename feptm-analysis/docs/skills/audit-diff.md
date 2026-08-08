# audit-diff — Audit Changed Files (delta vs baseline)

## Procedure

### Step 1: Detect changed files

For each repo directory listed by `sdd-cli context --list-names` (resolved to paths via workspace root `../`):

```bash
# For each repo short name from sdd-cli context --list-names,
# resolve path relative to workspace root (../<backend-repo>-{name} or ../<project>-web-{name})
cd {repo_path} && git diff --name-only HEAD 2>/dev/null
cd {repo_path} && git diff --name-only --cached HEAD 2>/dev/null
```

Collect repos that have changes. If none → "No changed files." STOP.

### Step 2: Check for active WF-*

```bash
ls ../<analysis-repo>/workflows/WF-*-*/session.yaml 2>/dev/null
```

If active WF-* exists with `status: implementing`:
- Read `baseline.yaml` from WF-* dir
- Delta mode: only NEW findings (not in baseline) are reported

If no active WF-*:
- Full mode: all findings reported

### Step 3: Run audit per repo

For each repo with changes, pick one changed file and run:

```bash
./scripts/sdd-cli.sh audit --files {repo_path}/{changed_file}
```

### Step 4: Report

For each repo:

```
## {repo-name} — PASS | WARN | FAIL

### New findings (not in baseline)
- ERR: {finding}
- WARN: {finding}

### Pre-existing (in baseline, not blocking)
- {finding}

Summary: {N} new ERR, {M} new WARN
```

If delta mode and zero new findings → "No new violations. Safe to commit."
