# SDD Context: feptm-server — FR-PROJECT-001

## Repo: feptm-server

### Identity

**Role:** service

**Ports:**

- http: 8000

**Config prefix:** `FEPTM_FEPTM_SERVER__`

**Functional requirements:** FR-PAYMENT-001, FR-SPECIALIST-001, FR-SYNC-001, FR-SYNC-RATES-001

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

#### AR-ARCH-001: Storage Abstraction Layer (Repository Pattern)

**Requirements:**

- Business logic services MUST depend on Protocol interfaces, not on the concrete GoogleSheetsService class.
- Every storage concern (project data, specialist data, sheet formulas) MUST have a corresponding Protocol defining its public contract.
- GoogleSheetsService MUST be injected into storage implementations via their constructors, not imported as a module-level singleton.
- Storage class methods MUST expose domain-level operations (e.g., add_specialist, get_metadata) — never expose raw Google Sheets API primitives (spreadsheet_id, range, A1Notation).
- Storage Protocol method signatures MUST use domain types (Project, Specialist, str IDs), not googleapiclient types or raw dicts.
- The TimesheetProjectService facade MUST depend on storage Protocols, not on GoogleSheetsService directly.

**Prohibitions:**

- Business logic or API handlers calling googleapiclient.discovery.Resource methods (spreadsheets().values().get(), etc.) directly.
- Services accessing self.google_sheets_service.sheets_service — bypassing the storage abstraction layer to call raw Google API.
- Business logic constructing A1Notation range strings (e.g., 'Sheet1!A1:B20') — ranges must be encapsulated in storage classes.
- Business logic constructing Google Sheets formulas (HYPERLINK, IMPORTRANGE, SUMIF) inline — formulas must be generated by storage classes or ConfigStorage.
- Business logic calling update_range, batch_update, clear_range directly — these are storage implementation details.
- Multiple storage classes implementing the same concern without a shared Protocol — pick one canonical abstraction per concern.

#### AR-ARCH-002: Dependency Injection

**Requirements:**

- All service classes MUST receive their dependencies via constructor arguments — never via module-level imports of singletons.
- All storage class dependencies MUST be received via constructor arguments — never via module-level imports of singletons.
- Stateful objects (services, storage classes, API clients) MUST NOT be instantiated at module level.
- API handlers MUST obtain service instances via FastAPI Depends() or an explicit factory function in a dependencies module.
- Configuration values (template IDs, folder IDs) MUST be injected into services at construction time, not read from a global settings object inside business logic methods.
- The application composition root (where dependencies are wired together) MUST live in a single module: src/feptm/dependencies.py.

**Prohibitions:**

- Module-level instantiation of stateful classes: ServiceClass() or StorageClass() at file scope outside of a dedicated factory function.
- Module-level singleton assignment: service = GoogleSheetsService() in any module.
- Business logic reading settings.GOOGLE_* environment variables directly — inject these values through the constructor.
- Services importing each other at module level (avoid circular dependency via constructor injection).

#### AR-ARCH-003: Service Layer Boundaries

**Requirements:**

- TimesheetProjectService MUST be a thin facade — orchestration only, ≤200 lines. All spreadsheet manipulation MUST be delegated to storage classes.
- SpecialistService MUST be a thin facade — orchestration only, ≤150 lines. All sheet reading/writing MUST be delegated to storage classes.
- ConfigService MUST be a thin facade — formula lookups delegated to ConfigStorage, enums remain as domain constants.
- The api/ layer MUST contain only: request validation, service orchestration calls, and response formatting. Zero business logic.
- Specialist tab creation, row insertion, formula assignment, and formatting copy MUST live in ProjectStorage or SpecialistStorage — never in the facade.
- Specialist parsing (headers map, row-to-Specialist conversion) MUST live in SpecialistStorage — never in the facade.

**Prohibitions:**

- Api handlers calling storage classes directly — always route through a service facade.
- Api handlers performing spreadsheet operations (creating sheets, writing ranges, syncing data).
- Storage classes calling other storage classes — cross-storage orchestration is the facade's responsibility.
- Facade methods that span more than 30 lines — extract into a dedicated method on the appropriate storage class.

#### AR-ARCH-004: Config-Driven Spreadsheet Layout

**Requirements:**

- All A1Notation range strings MUST be defined in RangeFormat enum or equivalent centralized config — never inlined in business logic.
- Spreadsheet column limits, row limits, and row counts MUST be configurable constants, not magic numbers with 'large enough' comments.
- Spreadsheet titles (e.g., '{name} - Project info') MUST be generated by a single title factory function, not inlined in create_project.
- URL patterns for Drive folders and spreadsheets MUST be defined once in UrlPattern enum or equivalent — never duplicated across models and services.
- Google Sheets formula templates (HYPERLINK, IMPORTRANGE, SUMIF) MUST use named-placeholder substitution (e.g., {timesheet_id}) not hardcoded string.replace() with magic strings.
- Template IDs for spreadsheet creation MUST be iterable — create_project() must accept a list of template descriptors, not hardcode three separate calls.
- The list of project spreadsheets (info, report, calculations) and their titles MUST come from configuration, not be enumerated in create_project()'s body.

**Prohibitions:**

- Hardcoded A1Notation ranges in any source file outside of config/enum definitions.
- Hardcoded row or column index limits with comments like 'large enough number to cover all columns'.
- Hardcoded HYPERLINK formula strings (=HYPERLINK("...")) in business logic.
- Hardcoded IMPORTRANGE formula strings with string.replace('SpecialistSpreadsheetID', ...) as a placeholder mechanism.
- URL patterns (docs.google.com/spreadsheets/d/, drive.google.com/drive/folders/) in model computed_field properties.
- create_project() hardcoding exactly three spreadsheets — use a template registry or configuration list.

#### AR-DATA-001: Specialist Row Identity

**Requirements:**

- When two or more specialists share the same name in the Team sheet, the server MUST log an ERROR-level message listing all duplicate names with row indices and abort the sync operation — no specialists are processed.
- The Specialist model MUST carry a row_index: int field populated from the source Team sheet row during list_from_sheet.
- All storage operations that write data to a specific Team sheet row (update_timesheet_ids) MUST target the row by row_index, not by name-based lookup.

**Prohibitions:**

- Silently dropping or overwriting a specialist when a name collision is detected.
- Disambiguating specialist names with row-based suffixes in tab names, Current Period rows, or archived period sheets.
- Storage operations matching specialists by raw name string alone for write-back into the Team sheet.

#### AR-ARCH-005: Google Sheets API Resilience

**Requirements:**

- All Google Sheets API write calls (batch_update, update_range, clear_range) in google_sheets_service.py MUST be wrapped with retry logic that handles HTTP 429 (Rate Limit) and 5xx (Server Error) responses.
- Retry strategy MUST use exponential backoff with jitter: initial delay 1s, max delay 60s, maximum 5 retries.
- Retry logic MUST honor the Retry-After response header when present on 429 responses, using it as a minimum wait before the next attempt.
- The retry wrapper MUST be implemented as a shared decorator or utility in the GoogleSheetsService class, not duplicated per-method.
- Google Sheets API calls that exhaust all retries MUST log the failure at ERROR level with the spreadsheet ID, operation name, and error details, then raise a domain-specific exception (GoogleSheetsRateLimitError or GoogleSheetsServerError).
- Long-running batch operations spanning multiple API calls (e.g., sync loops over specialists) MUST include a throttling mechanism to avoid exceeding the per-minute write quota (default: 60 requests per minute per user).
- The throttling mechanism MUST be a shared rate-limiter utility (token bucket or sliding window) reusable across all storage operations, not ad-hoc sleep calls in business logic.

**Prohibitions:**

- Calling googleapiclient .execute() on batchUpdate, values().update, or values().clear without prior retry wrapper.
- Catching bare Exception around Google Sheets API calls and silently swallowing rate-limit or server errors.
- Hardcoding time.sleep() or asyncio.sleep() inline in storage or business logic to work around rate limits — use the shared rate-limiter utility.
- Infinite retry loops with no maximum retry count or timeout ceiling.
- Duplicating retry or backoff logic across storage modules — the resilience layer lives in GoogleSheetsService only.

