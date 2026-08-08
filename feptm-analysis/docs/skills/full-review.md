# Full Review

A holistic sanity-check that goes beyond a single-PR review or a per-rule audit. Aim is to surface (a) drift between what the project claims and what is true, (b) AR specs that look enforcing but actually self-disable, (c) the long-tail concerns that single-axis reviews miss.

Read-only: this procedure must NOT edit, write, or commit. It produces a report.

## When to invoke

- After a significant WF closes — find ripple effects.
- Before a release / merge to main.
- Periodic health check (monthly / quarterly).
- After "wrap-it-up"-style sweeps to find the long tail.

## Output

A single markdown report at the end of the run, in chat. Structure:

```markdown
# Full Review — {YYYY-MM-DD}

## TL;DR
{1–2 sentences. Counts: N BLOCK / N NEEDS-FIX / N NICE-TO-HAVE.}

## Findings

### BLOCK ({n})
- [{phase}] {finding} — {evidence: file:line or command output}

### NEEDS-FIX ({n})
- [{phase}] {finding} — {evidence}

### NICE-TO-HAVE ({n})
- [{phase}] {finding}

## Coverage matrix

| Phase | Status | Notes |
|---|---|---|
| 1. Native checks | PASS / FAIL / N-A | |
| 2. SDD compliance | ... | |
| ... | ... | |

## Top 5 recommendations
1. ...
```

## Severity rubric

- **BLOCK** — production / methodology / security integrity threatened. Cannot ship as-is.
- **NEEDS-FIX** — clear bug, gap, or false claim; address before next milestone.
- **NICE-TO-HAVE** — improvement; no urgency.

## Phases

Work through every phase. If a phase is not applicable to the current state of <project>, mark it N-A in the matrix with a one-line reason.

### Phase 0 — Read declared non-goals

Before running any checks, read `<workspace-repo>/README.md` § Scope and non-goals. Each bullet there names a phase (or a subset of one) that has been consciously declined with documented rationale. For every match:

- Mark the listed phase **N-A** in the coverage matrix; cite the rationale verbatim or with a short paraphrase pointing back to `README.md § Scope and non-goals`.
- Do NOT emit BLOCK / NEEDS-FIX / NICE-TO-HAVE findings for that phase or subset.
- A subset call-out (e.g. "a11y + i18n within Phase 11") suppresses only those items — checks elsewhere in the same phase still run normally.

If the Scope and non-goals section is missing, behave as if every phase is in scope. If a finding you would otherwise raise is plausibly a non-goal but not listed, raise it as NICE-TO-HAVE with a note suggesting the user record it in Scope and non-goals to suppress future warnings — do NOT silently skip it.

### Phase 1 — Native checks (ground truth)

Run every native quality gate first. Each non-zero exit = BLOCK.

```bash
# Backend Rust
(cd ../<backend-repo> && cargo check --quiet && cargo clippy --all-targets -- -D warnings && cargo fmt --check && cargo test --quiet)
# Proto Rust SDK
(cd ../<proto-repo>/sdk/rust && cargo check --quiet)
# TypeScript SDK
(. ~/.nvm/nvm.sh && nvm use 20 >/dev/null && cd ../<proto-repo>/sdk/typescript && pnpm run check)
# Storefront
(. ~/.nvm/nvm.sh && nvm use 20 >/dev/null && cd ../<webapp-repo> && pnpm exec tsc --noEmit && pnpm lint && pnpm format:check)
# Codegen drift
./scripts/check-codegen-drift.sh
# SDD audit (workspace level)
./scripts/sdd-cli.sh audit
# Build (storefront)
(. ~/.nvm/nvm.sh && nvm use 20 >/dev/null && cd ../<webapp-repo> && pnpm build)
```

### Phase 2 — SDD compliance

- Every repo declared in `repo-spec.yaml`; `role` matches the schema enum.
- `role-templates.yaml` covers every role used; AR specs attached to each role exist as `.yaml` files.
- `@req` traceability:
  - `./scripts/sdd-cli.sh verify --phase finalize` exits 0; orphan-delta count is 0. (A standalone `traceability` subcommand is on the [roadmap](../../docs/ROADMAP.md).)
  - Each REST handler has `@req`. Count of `@req`-bearing handlers ≥ count of operations in OpenAPI.
  - Domain / repo / utility layers do NOT carry `@req` (per AR-LINEAGE-001).
- AR-spec self-consistency — for each AR spec with `checks:`:
  - Grep for `skip_if:\s*\n\s*file_missing:` patterns where the missing file is the same as `required:` — that is the self-disable bug we hit on AR-LINT-001.
  - Open the spec, simulate the check by hand on at least one file, confirm it would actually fail when violated.
- All open `WF-*/session.yaml` have `status: done` or are explicitly in-progress with a note in STATUS.md.
- For every closed WF: `archive/plan-NNN.md` and `archive/tasks-NNN.md` exist.
- Generated artifact discipline (AR-CODEGEN-001):
  - Every `*_gen.{rs,ts}` file has the project header at line 1.
  - `.gitignore` does not exclude `generated_gen/` or `src/gen/`.
  - Generator deps are commit-pinned (Rust) or exact-version (npm). Grep for `branch =` and `^|~` on the generator names.
  - `scripts/check-codegen-drift.sh` exits 0.
- PostToolUse hook in `.claude/settings.json` references the drift script and the matcher fires on `Edit|Write` of `*.openapi.yaml`.

### Phase 3 — Code quality

Rust:
- No `unwrap()`, `expect(`, `panic!()`, `todo!()`, `unimplemented!()` outside `tests/` and `build.rs` — grep with file filter.
- No `#[allow(dead_code)]` without an inline `AR-HYGIENE-001:allow ...` justification.
- No `as` casts that lose precision without a paired bounds check (we did `i64 as u32` — verify `narrow_*` helpers always check first).
- Error types implement `IntoResponse` / mapping to HTTP consistently.
- No magic numbers — extracted to `const`.

TypeScript:
- `tsconfig.json` has `strict: true` (and ideally `noUncheckedIndexedAccess`).
- No `: any` (or every `any` is paired with an `// AR-TYPESCRIPT-001:allow` style note).
- No `console.log` (only `warn|error|info|debug` per AR-LINT-001).
- No locally-declared types that mirror generated SDK types.

Cross-cutting:
- Lockfiles committed and `--frozen-lockfile`-friendly.
- No commented-out code blocks (5+ consecutive `//` lines that look like code).

### Phase 4 — Test coverage

- Every endpoint has at least one happy-path integration test. Cross-reference operationIds in `<project>.openapi.yaml` against test names.
- Negative paths covered: 400 (validation), 404 (not found), 409 (conflict, e.g. insufficient stock).
- Concurrency edges: checkout race (two clients hitting `/checkout` for the same cart), cart mutation while another caller iterates.
- No `#[ignore]`, `xtest`, `.skip`, `it.only`, `describe.only` markers.
- Test names describe behavior, not implementation.
- Coverage tool configured (`cargo tarpaulin` / `cargo llvm-cov`)? If yes, threshold enforced. If no — flag as NEEDS-FIX or NICE-TO-HAVE depending on project maturity.
- Storefront E2E (Playwright / Cypress)? If absent — NICE-TO-HAVE for demo, NEEDS-FIX for production posture.
- API-contract tests (schemathesis / dredd / openapi-spec-validator on responses)? Without these, the codegen pipeline guarantees DTO shape but not handler conformance.

### Phase 5 — Quality gates (CI / hooks)

- CI present (`.github/workflows/`, `.gitlab-ci.yml`, etc.) — or admit absence.
- If CI: it runs cargo build/test/clippy, pnpm lint/build, and `sdd-cli verify` on PRs.
- Pre-commit hook (`.git/hooks/pre-commit`, husky, lefthook) for fast checks.
- PostToolUse hook fires `check-codegen-drift.sh` on spec edits.
- Dependency vulnerability scan: `cargo audit`, `pnpm audit --audit-level high`.
- Secret scan: gitleaks / trufflehog at least pre-commit.
- License compatibility check on transitive deps.

### Phase 6 — Documentation fidelity

- `CLAUDE.md` paths: every `[name](relative/path)` link resolves on disk.
- `CLAUDE.md` claims match reality:
  - AR-spec counts ("N specs across M categories" — grep and count; never assume — re-derive).
  - File paths and module names current.
  - Versions of generators / runtimes match what's actually in `Cargo.toml` / `package.json`.
- Top-level `README.md` explains: what the project is, how to run it locally, how to contribute.
- `CONTRIBUTING.md` exists and describes the SDD workflow for newcomers (init-task → plan-task → implement-task → finalize-task).
- `LICENSE` at repo root.
- `CHANGELOG.md` or git tags for releases.
- Each WF-* has a `decisions.md` if any judgement calls were made (alternative considered, rejection rationale).
- AR specs have non-empty `context:` field (most ship with empty `context: ""` — flag as NICE-TO-HAVE batch).
- ADRs (Architecture Decision Records) for cross-cutting calls.

### Phase 7 — Security

- No secrets in git history: `git log -p | grep -iE 'secret|password|token|api[_-]key|bearer'` plus gitleaks-style sweep.
- `.env*` patterns gitignored at every level.
- Input validation at every external boundary (handlers, query parsers, request bodies).
- CORS configured, or explicit decision in `decisions.md` ("same-origin via Next rewrite — no CORS surface").
- Rate limiting / DOS protection (or admitted absence with rationale).
- AuthZ surface — any auth at all? If "no auth — demo project", that's a decision worth recording.
- Dep vuln audit run, no high/critical findings.
- `SECURITY.md` (vulnerability disclosure policy).
- Threat model document for non-trivial systems.

### Phase 8 — Observability

- Structured logging (json-format option vs text) appropriate for env.
- Log levels matched to call type per AR-WRITING-001 / project convention (`debug!` for GET, `info!` for mutations).
- No PII / secrets in logs (`tracing::field` style spans).
- Request id / correlation id propagation.
- Metrics (Prometheus / OTel) for request rate, error rate, p99 latency.
- Distributed tracing (OTel spans across handler → repo → external).
- Health check endpoint (`/healthz` or `/health`) — readiness vs liveness.

### Phase 9 — Operations

- Dockerfile / container image present and minimal (multi-stage, non-root user).
- Deploy manifest (k8s, compose, terraform) versioned alongside code.
- `.env.example` with every config key documented.
- Backup / restore procedure (N-A for in-memory demo — record as such).
- Rollback procedure.
- Runbook for common ops (start, stop, regen, drift fix).

### Phase 10 — Performance (light pass)

- No sync I/O inside `async fn` (no `std::fs::read` etc.).
- Lock contention: any `RwLock`/`Mutex` held across long operations? (We hold a write lock for the entire checkout transaction — flag the scope.)
- N+1 patterns in repos.
- Storefront bundle size: `pnpm build` summary; flag any chunk >250 KB gzipped.
- p99 latency / load test (admit absence if none).

### Phase 11 — Frontend specifics

- Accessibility: semantic HTML (`<button>` not `<div onclick>`), ARIA attrs, focus management, color contrast. Run `axe-core` or admit absence.
- SEO: title / meta description per route, OpenGraph tags, sitemap, robots.txt.
- Browser compat target list.
- Core Web Vitals (LCP / CLS / INP) awareness.
- Dark mode / theming.
- i18n posture (even if single-language now, infrastructure ready?).

### Phase 12 — Governance / community

- `CODE_OF_CONDUCT.md`.
- `SECURITY.md` (covered in Phase 7 too).
- PR template (`.github/pull_request_template.md`).
- Issue templates.
- `CODEOWNERS` file.
- Branch protection rules (cannot inspect from local clone — record as "verify on remote").
- Release process / versioning policy (SemVer? CalVer?).

## Reporting checklist

Before posting the report, verify:

- [ ] Every BLOCK has concrete evidence (file:line or command output).
- [ ] Every NEEDS-FIX has a one-line "what to do" (not just "X is wrong").
- [ ] N-A entries in the matrix have a one-line reason.
- [ ] Top-5 recommendations are sorted by impact-per-effort, not severity.
- [ ] No fixes are applied — this is read-only.

## Stop conditions

- All 12 phases processed.
- Report posted in chat.

Do NOT invoke `/checkpoint` or `/finalize-task` — full-review does not produce commits or change WF state.
