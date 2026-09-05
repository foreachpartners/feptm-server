# SDD Context: web — FR-THEME-001

## Repo: feptm-web

### Identity

**Role:** webapp

**Ports:**

- http: 3000

**Functional requirements:** FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001, FR-SYNC-001, FR-SYNC-RATES-001, FR-PAYMENT-001, FR-THEME-001

### Applicable Rules

#### AR-LINEAGE-001: @req Annotation Format

**Requirements:**

- Annotate with `@req {TYPE}-{CATEGORY}-{NNN}[, {TYPE}-{CATEGORY}-{NNN}]*` where TYPE is FR or AR.
- Place `@req` as `# @req FR-*` comment on the line directly above the function/class definition in Python.
- Annotate every REST handler function (e.g., FastAPI route handler) that implements a requirement.
- Annotate at the contract boundary: handler implementation.

**Prohibitions:**

- @req in service/business logic layer functions (traced through handler).
- @req in repository / storage layer functions (infrastructure, traced through handler).
- @req on shared utility functions unless the utility exists solely for one requirement.

#### AR-LINEAGE-002: Commit Message Format

**Requirements:**

- Format commit messages as `{type}(scope): message [ID]` or `{type}(scope): message [ID, ID, ...]` where each ID is `FR-{CATEGORY}-{NNN}` or `AR-{CATEGORY}-{NNN}`.
- Every behavioral change commit (feat, fix, refactor) MUST include at least one requirement ID in brackets at the end of the subject line.
- Use conventional commit types: feat, fix, refactor, test, docs, chore, ci.
- Scope MUST match the affected repo or module name.
- Use a comma + single space (`, `) to separate multiple IDs inside one bracket: `[FR-CART-001, AR-LINT-001]`.

**Prohibitions:**

- Behavioral commits (feat, fix, refactor) without a requirement ID reference.
- Requirement IDs outside brackets or not at the end of the subject line.
- Multiple bracket blocks on one subject. Always combine IDs into a single comma-separated bracket.

#### AR-SECRETS-001: Secret Protection

**Requirements:**

- Mask any field carrying a secret (key, token, password, credential) when implementing __repr__, __str__, or any logging path.
- Implement __repr__ manually for classes that hold secret fields; do not rely on default.

**Prohibitions:**

- Log secrets (encryption keys, API keys, tokens, DB credentials) via logging.debug, print, or any logging path.
- Include secrets in error messages or error types.
- Hardcode secrets in source — load from env at startup or from a secret store.
- Commit backup/scratch files (*.bak, *.backup, *.orig) that may carry pre-redaction content.

#### AR-WORKSPACE-001: Workspace Overview

**Requirements:**

- Treat feptm-workspace/README.md as the single source of truth for workspace structure.
- Architecture: single backend service (FastAPI) backed by Google Sheets as the data store, behind nginx reverse proxy.
- Tech stack: Python 3.12+, FastAPI 0.110+, Google Sheets API v4, OAuth 2.0, uv package manager, uvicorn ASGI server, Ubuntu 24.04 LTS, nginx, systemd.
- Sibling repos that compose the project, each conceptually a separate repo: feptm-server (backend service), feptm-analysis (specs + workflows + docs), feptm-workspace (skills + settings + scripts).
- Local ports: backend HTTP :8000.
- Audit and context CLI live in fep-sdd; consume via feptm-workspace/scripts/sdd-cli.sh wrapper.

**Prohibitions:**

- Duplicate workspace structure information — link to feptm-workspace/README.md instead.
- Hardcode absolute paths in scripts — resolve from $0 or use workspace-relative paths.

#### AR-WRITING-001: LLM-Oriented Writing Style

**Requirements:**

- Use imperative, directive language: 'Load ENV at startup.' not 'First, we''ll load ENV...'.
- Prioritize clarity over brevity; brevity over all else.
- Use MUST for mandatory rules, SHOULD for recommended, MAY for optional, DO NOT for prohibited.
- Fix all ERR findings from the llm-writing check before publishing.
- Fix all WARN findings from the llm-writing check before publishing.

**Prohibitions:**

- Motivational phrases: 'Great job!', 'Perfect!', 'Excellent!'.
- Uncertainty markers: 'maybe', 'perhaps', 'I think'.
- Filler words: 'basically', 'essentially', 'actually'.
- Apologies: 'sorry', 'unfortunately'.
- Conversational check-ins: 'Make sense?', 'Got it?'.
- Subjective qualifiers: 'elegant', 'beautiful', 'clean'.
- Non-English text in rules and documentation.

