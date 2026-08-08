# checkpoint — Intermediate Commit During Implementation

CLI tool: `./scripts/sdd-cli.sh`
Workflow directory: `<analysis-repo>/workflows/WF-*-*/`


Commits current work-in-progress for the active WF-* workflow. Generates commit message with FR-* IDs from session.yaml. Does NOT archive plan/tasks. Does NOT require all tasks done.

### Usage

```
/checkpoint                                      # auto-detect WF-* dir
/checkpoint WF-2                                # explicit WF-* dir
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

Persist to `WF-*/session.yaml` — add or update `sessions` mapping (write only the `checkpoint` key). If multiple checkpoints in one session, only the first write is needed.

### Step 1: Find WF-* directory

Same as Phase 3 Step 1 — look for `status: implementing`.

### Step 2: Load context

Read `session.yaml` — extract `fr_ids`, `repos`.

### Step 3: Optional verification

Run verification in terminal:

```bash
./scripts/sdd-cli.sh verify --wf-dir {wf_dir} --phase implement
```

If exit code 2 → show findings. Ask user: "Verification found new issues. Commit anyway?" If user declines → STOP. If user confirms or verification passed → continue.

Record result: `verified: true|false`.

### Step 4: Collect changes per repo

For each repo in `session.yaml`:

```bash
cd {repo_path} && git diff --stat HEAD
cd {repo_path} && git diff --stat --cached HEAD
```

If no changes in any repo → "Nothing to commit." STOP.

### Step 5: Generate commit message

Format: `WF-{ID}: {summary} [{FR-IDs}]`

- `{ID}` — from WF-* directory name
- `{summary}` — concise description of changes from diff analysis (the "why", not "what")
- `{FR-IDs}` — space-separated FR-* IDs from `session.yaml` `fr_ids` field. MANDATORY.

Example: `WF-1: add API data seeding for E2E tests [FR-AUTH-001 FR-CATALOG-001 FR-CHECKOUT-002 FR-INVENTORY-003]`

Present to user for confirmation. User may edit the message.

### Step 6: Commit

For each repo with changes:

1. Show `git status --short` to the user
2. Stage only tracked files (modified + deleted): `git add -u`
3. If there are untracked files, list them and ask user: "Also stage these untracked files?" Stage confirmed files with `git add {file}`.
4. Commit: `git commit -m "{message}"`

```bash
cd {repo_path} && git status --short
cd {repo_path} && git add -u && git commit -m "{message}"
```

DO NOT use `git add -A` — it may stage secrets, build artifacts, or unintended files.

### Step 7: Record checkpoint

Add entry to `session.yaml` `checkpoints:` list:

```yaml
checkpoints:
  - date: "YYYY-MM-DD"
    commit: "{short_hash}"
    repos: [repo1, repo2]
    summary: "{summary from commit message}"
    verified: true|false
```

Update `STATUS.md`: append checkpoint entry to History table.

### Step 8: Report

```
Checkpoint committed:
  {repo1}: {short_hash}
  {repo2}: {short_hash}
Message: WF-{ID}: {summary} [{FR-IDs}]
Verified: yes|no
Session: {CLAUDE_SID}
```

**STOP.** Continue with `/implement-task` or `/finalize-task`.

---
