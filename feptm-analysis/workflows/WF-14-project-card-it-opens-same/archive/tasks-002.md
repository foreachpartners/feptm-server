# WF-14: Tasks

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Rewrite: add `/api/projects/:driveFolderId/` -> `${apiOrigin}/api/projects/:driveFolderId/` in `feptm-web/next.config.ts` after the list rules and before the `/api/:path*` catch-all. Keep `skipTrailingSlashRedirect`, `resolveApiOrigin`, and existing list rules. Do not add a no-slash `:driveFolderId` rule | FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001 | — | done | 2026-09-05T16:45 |
| T-02 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-PROJECT-001, FR-CREATE-001, FR-SHEET-001, FR-SYNC-001, FR-SYNC-RATES-001, FR-PAYMENT-001 | T-01 | done | 2026-09-05T16:48 |
