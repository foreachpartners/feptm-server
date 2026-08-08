# finalize-task — Prepare Final Commit

CLI tool: `./scripts/sdd-cli.sh`
Workflow directory: `<analysis-repo>/workflows/WF-*-*/`


Prepares commit for WF-* workflow artifacts and implementation code changes. Generates commit message, shows dry-run. Does NOT auto-commit.

### Usage

```
/finalize-task                                    # auto-detect WF-* dir
/finalize-task WF-3                              # explicit WF-* dir
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

Persist to `WF-*/session.yaml` — add or update `sessions` mapping (write only the `finalize` key).

### Step 1: Find WF-* directory

Same as Phase 3 Step 1, but look for `status: implementing` or `status: done`.

Run in terminal:

```bash
ls ../<analysis-repo>/workflows/WF-*-*/session.yaml 2>/dev/null
```

Read each session.yaml, check `status` is `implementing` or `done`.

Decision table:

| Found | Action |
|-------|--------|
| Exactly 1 | Use it |
| Multiple | List all, ask user to pick |
| None | Error: "No active workflow. Run /implement-task first." |

### Step 2: Collect changes

1. Read `session.yaml` — FR IDs, repos
2. Read `tasks.md` — verify all tasks are `done` or `blocked`
3. Collect modified files across all repos listed in session.yaml:

```bash
cd {repo_path} && git diff --name-only HEAD
cd {repo_path} && git diff --name-only --cached HEAD
```

4. Collect WF-* directory artifacts:

```bash
ls {wf_dir}/*.md {wf_dir}/*.yaml
```

### Step 3: Verification gate

Run full verification (cargo check/clippy/test, AR audit delta, task-diff, traceability) in terminal:

```bash
./scripts/sdd-cli.sh verify --wf-dir {wf_dir} --phase finalize
```

Only NEW findings (not in baseline.yaml) block. Pre-existing issues are reported but do not block.

If exit code 2 → **HARD STOP**. Do NOT proceed to Step 4. Do NOT archive. Do NOT generate commit message. Output the following block and STOP:

```text
## VERIFICATION FAILED — BLOCKING

WF-{ID}-{slug}: verification gate did not pass (exit code 2)

Failures:
- {list each failure from verify output}

Action required: fix failures and re-run `/finalize-task`.
No artifacts were archived. No commit prepared.
```

**STOP HERE.** Wait for user to fix issues. Do NOT continue under any circumstances.

### Step 4: Archive active artifacts (ONLY if Step 3 exit code 0)

1. Create archive directory if it doesn't exist:

```bash
mkdir -p {wf_dir}/archive
```

2. Determine next sequence number: count existing `plan-*.md` files in `archive/`, increment by 1. Format: 3-digit zero-padded (001, 002, etc.).

```bash
ls {wf_dir}/archive/plan-*.md 2>/dev/null | wc -l
```

3. Move active plan.md and tasks.md to archive:

```bash
mv {wf_dir}/plan.md {wf_dir}/archive/plan-{NNN}.md
mv {wf_dir}/tasks.md {wf_dir}/archive/tasks-{NNN}.md
```

4. Append row to STATUS.md History table:

```bash
echo "| {NNN} | [plan-{NNN}.md](archive/plan-{NNN}.md) | [tasks-{NNN}.md](archive/tasks-{NNN}.md) | {today's date} | Implemented |" >> {wf_dir}/STATUS.md
```

### Step 5: Generate commit message

Single-line format — file lists are DRY violation (`git diff --stat` provides them):

```
WF-{ID}: {summary} [{FR-IDs}]
```

Example: `WF-3: complete GET /me handler — typed DTOs, error handling, @req [FR-AUTH-006]`

### Step 6: Dry-run and present

Show `git status --short` for each repo with changes, then present:

```
WF-{ID}-{slug} — ready to commit

Commit: WF-{ID}: {summary} [{FR-IDs}]
Session: {CLAUDE_SID}
Verification: sdd-cli verify --phase finalize ✓
```

**Acceptance criteria:**

- [ ] All tasks `done` or `blocked`
- [ ] plan.md + tasks.md archived
- [ ] `sdd-cli verify --phase finalize` passed (exit 0)
- [ ] No auto-commit

**STOP.** Do NOT commit. User decides when and how to commit.
