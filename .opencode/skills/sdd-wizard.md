# sdd-wizard — All-in-One Feature Flow

Chains the full SDD pipeline from initiation through commit in one guided flow. This is the recommended entry point for building features.

## Usage

Say "run sdd-wizard Implement <feature description> per FR-XXX-NNN" and follow the prompts.

The wizard auto-chains through the phases, stopping at key gates for your review.

## Procedure

### Phase 1: Init

Locate repos and FRs, initialize workflow, capture baseline.

1. Read `feptm-analysis/docs/conventions/session-context.md` for workspace context.
2. Run `./scripts/sdd-cli.sh context --scope` from `feptm-workspace/`.
3. If user specified `per FR-XXX-NNN`, read that FR spec from `feptm-analysis/fr-specs/FR-XXX-NNN.yaml`.
4. Determine affected repos from FR content and scope output.
5. Run `./scripts/sdd-cli.sh init --name <repo>... --fr FR-XXX-NNN --description "..."`.
6. Run `./scripts/sdd-cli.sh verify --wf-dir <wf_dir> --phase init` (baseline).
7. Generate session ID and persist to `session.yaml`.
8. Present summary.

**Gate 0**: Confirm repo scope and FRs. Proceed.

### Phase 2: Plan

Draft technical plan, stop for review.

1. Generate session ID, persist to `session.yaml` (`sessions.plan`).
2. Load `context.md`, `session.yaml`, `baseline.yaml`.
3. Ask user about baseline policy if violations exist.
4. Draft `plan.md` covering architecture, API changes, storage, implementation, security, config.
5. Write `WF-*/plan.md`.

**Gate 1 — HARD STOP**: Present plan for review. Wait for user to edit and approve.

### Phase 3: Implement (after plan approval)

Execute tasks, verify each.

1. Re-read `plan.md` (user may have edited).
2. Generate `tasks.md` with ordered tasks.
3. Update `session.yaml`: `status: planned`.
4. Execute each pending task:
   - Mark `in_progress`
   - Implement changes (edit files, run `make typecheck`)
   - Run `./scripts/sdd-cli.sh verify --wf-dir <wf_dir> --phase implement`
   - Mark `done` or `blocked`
5. Run finalize-phase verification.
6. Present implementation report.

### Phase 4: Finalize

Archive, verify, prepare commit.

1. Verify all tasks done (or blocked reported).
2. Run `./scripts/sdd-cli.sh verify --wf-dir <wf_dir> --phase finalize`.
3. If exit 2 → **HARD STOP**, report failures.
4. Archive `plan.md` and `tasks.md` into `archive/plan-NNN.md` / `archive/tasks-NNN.md`.
5. Append to `STATUS.md` History.
6. Generate commit message: `WF-{ID}: {summary} [{FR-IDs}]`.
7. Show `git status --short` per repo.

**Gate 2**: Present commit dry-run. User decides "commit" or "abort".

## Key Rules

- Never proceed past a gate without explicit user approval.
- All commands run from `feptm-workspace/`.
- Use `./scripts/sdd-cli.sh` for all fep-sdd operations.
- Read the source docs at `feptm-analysis/docs/skills/*.md` for detailed procedures.
