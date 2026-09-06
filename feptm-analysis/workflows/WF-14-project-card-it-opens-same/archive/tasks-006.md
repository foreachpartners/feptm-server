# WF-14: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Proxy: add `experimental.proxyTimeout: 300_000` in `feptm-web/next.config.ts`. Keep `resolveApiOrigin`, `skipTrailingSlashRedirect`, and the four `/api/*` rewrite rules. Do not change rewrite sources or destinations. Do not add a new env key. | FR-CREATE-001, FR-PAYMENT-001, FR-PROJECT-001, FR-SHEET-001, FR-SYNC-001, FR-SYNC-RATES-001 | — | done | 2026-09-06T19:18 |
| T-02 | Client: add `API_REQUEST_TIMEOUT_MS = 600_000` and pass `signal: AbortSignal.timeout(API_REQUEST_TIMEOUT_MS)` into `fetch` inside `requestJson` in `feptm-web/src/lib/api/projects.ts`. Keep the existing `catch` → `ApiClientError(fallbackMessage, 'network', null)`. Do not change the six FR error strings, HTTP 409 copy, or `@req` on the six exports. | FR-CREATE-001, FR-PAYMENT-001, FR-PROJECT-001, FR-SHEET-001, FR-SYNC-001, FR-SYNC-RATES-001 | T-01 | done | 2026-09-06T19:19 |
| T-03 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-CREATE-001, FR-PAYMENT-001, FR-PROJECT-001, FR-SHEET-001, FR-SYNC-001, FR-SYNC-RATES-001 | T-02 | done | 2026-09-06T19:20 |
