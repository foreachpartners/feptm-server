# init-task — Initialize SDD Workflow Context

CLI tool: `./scripts/sdd-cli.sh`
Workflow directory: `<analysis-repo>/workflows/WF-*-*/`


Creates WF-* workflow directory per SDD ceremony mapping. Generates context document, session state, and initial status. Outputs completeness summary.

### Usage

```
/init-task <short-name> [<short-name>...]     # direct mode
/init-task <free-form task description>        # scoping mode
```

Examples:

- `/init-task backend storefront` — direct: init context for the Rust backend and Next.js storefront
- `/init-task Add filtering by emotion category` — scoping: determine repos and FRs from description
- `/init-task Validate checkout atomicity under concurrent purchases` — scoping: determine repos and FRs from description

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

Persist to `WF-*/session.yaml` — add or update `sessions` mapping:

```yaml
sessions:
  init: "{uuid}"      # added by /init-task
  plan: "{uuid}"      # added by /plan-task
  implement: "{uuid}"  # added by /implement-task
  finalize: "{uuid}"  # added by /finalize-task
```

If `sessions:` key doesn't exist in session.yaml, add it. Each phase writes only its own phase key.

### Step 1: Detect mode

Check if ALL arguments match available short names.

Run in terminal:
```
./scripts/sdd-cli.sh context --list-names
```

- If ALL arguments are valid short names → **Direct mode** (go to Step 3)
- If ANY argument is NOT a short name → **Scoping mode** (go to Step 2)

### Step 2: LLM scoping (only for free-form input)

Run in terminal:
```
./scripts/sdd-cli.sh context --scope
```

Output: compact table of all repos (name, type, role, requirements with titles).

Analyze the user's task description against this table. Determine:

1. Which repos are affected — select the minimum set needed for the task.
2. Which FR IDs are relevant — identify from the Requirements column (format: `FR-CART-001 — Server-Side Cart`).

Example reasoning:

- "filter by emotion category" → catalog query logic in `backend` (service) + UI in `storefront` (webapp) + OpenAPI operation in `proto` → repos: `backend`, `storefront`, `proto`; FRs: `FR-CATALOG-001`, `FR-DISCOVERY-001`
- "checkout atomicity" → transactional logic in `backend` (single-monolith service) → repos: `backend`; FRs: `FR-CHECKOUT-001`, `FR-PURCHASE-001`, `FR-INVENTORY-001`
- "OpenAPI x-requirement annotations on operations" → contract in `proto` + handler-side @req tags in `backend` and `storefront` → repos: `proto`, `backend`, `storefront`; FRs: cross-cutting (whichever the touched operations cover)

State the selected repos, FR IDs, and reasoning before proceeding.

### Step 3: Initialize workflow

Build the `sdd-cli init` command from scoping results.

Run in terminal (main context, NOT a subagent):

```
./scripts/sdd-cli.sh init \
  --name <name1> --name <name2> \
  --fr FR-AUTH-016 --fr FR-CATALOG-001 \
  --description "<1-2 sentence task description>"
```

IMPORTANT:

- `--fr` is required. In direct mode, check the repo-spec.yaml requirements for the selected repos and include relevant FR IDs. If no FRs are apparent, ask the user.
- `--description` is required. Use the user's task description (or a concise summary of it). This names the workflow and helps match future init calls to existing workflows.

#### Candidate matching

`sdd-cli init` only flags a candidate when (a) the existing WF is **active** (`context_ready`, `planned`, `implementing`, `in_progress`) and (b) it shares at least one FR ID with the target. Done / abandoned workflows are never returned. Repo-overlap alone is not enough. If candidates ARE returned, the tool outputs candidates YAML and **does NOT create a new WF**. You MUST:

1. Present candidates to the user:

   ```text
   Found existing workflow(s) with overlapping scope:
   - WF-6-e2e-checkout-tests (score: 0.85, status: context_ready)
     Repos: qa, storefront-site, memberarea
     Description: "Develop E2E tests for storefront repos"
   ```

2. Ask: "Continue with WF-6-e2e-checkout-tests, or create a new workflow?"
3. Based on user response, **re-run the same `sdd-cli init` command** with `--wf <name>` (to reuse) or `--wf new` (to create fresh):

   ```bash
   ./scripts/sdd-cli.sh init \
     --name <...> --fr <...> --description "<...>" \
     --wf new                                          # or: --wf WF-6-e2e-checkout-tests
   ```

### Step 3.5: Baseline audit

Capture pre-existing audit state for later delta comparison during verification:

```bash
./scripts/sdd-cli.sh verify --wf-dir {wf_dir_absolute} --phase init
```

Where `{wf_dir_absolute}` is the absolute path to the WF-* directory from Step 3 output.

This saves `baseline.yaml` in the WF-* directory. Pre-existing findings do not block init.

### Step 4: Read and summarize

Read the output from Step 3. It contains:
- `wf_dir` — path to created/reused WF-* directory
- `ceremony` — ceremony level (minimal/small/medium/large)
- `status` — workflow status (context_ready)

Read `WF-*/context.md` first 30 lines (completeness table + scope).

Present summary using **clickable markdown links** for all paths. Use `../` prefix relative to workspace root (files are under `<analysis-repo>/`).

Example (assuming `wf_dir` = `<analysis-repo>/workflows/WF-4-add-emotion-category-filter`):

```
WF-4-add-emotion-category-filter initialized (medium ceremony)

| Artifact | Path |
|----------|------|
| Folder | [WF-4-add-emotion-category-filter](../<analysis-repo>/workflows/WF-4-add-emotion-category-filter/) |
| Context | [context.md](../<analysis-repo>/workflows/WF-4-add-emotion-category-filter/context.md) |
| Session | [session.yaml](../<analysis-repo>/workflows/WF-4-add-emotion-category-filter/session.yaml) |
| Status | [STATUS.md](../<analysis-repo>/workflows/WF-4-add-emotion-category-filter/STATUS.md) |
| Baseline | [baseline.yaml](../<analysis-repo>/workflows/WF-4-add-emotion-category-filter/baseline.yaml) |

Completeness FR-CATALOG-001: 8/10 ok
  Missing (optional): Test Files, Git Commits
Session: {CLAUDE_SID}

Next: `/plan-task <task description>`
```

**Acceptance criteria** — verify your output before presenting:

- [ ] Every file path uses `[name](relative-path)` markdown link syntax (NO backticks)
- [ ] Links use `../<analysis-repo>/...` prefix (relative to workspace root)
- [ ] Completeness line includes FR ID, ok/total count, and missing items
- [ ] Output ends with `Next:` suggestion

### Step 5: End of phase

The init phase ends here. What happens next depends on **how you got here**:

- **Standalone `/init-task` invocation** → STOP. Wait for the user's next command. Do NOT enter plan mode, do NOT start implementation, do NOT launch exploration agents.
- **Chained from a higher-level intent** ("implement X", or any prompt that asks for the whole feature) → proceed directly to `/plan-task` on the same turn. The user has already authorized full execution; the canonical user gate is the hard stop after `plan.md` is drafted (plan-task Step 5), not here.

> **Tip:** Run `/branch-task` next to create feature branches across all workspace repos before planning. The branch name is auto-generated from the WF-* slug. This step is optional — you can also branch manually or skip if branches already exist.

---
