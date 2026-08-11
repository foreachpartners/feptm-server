# Tasks: Google Sheets API Resilience (AR-ARCH-005)

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-38 | Service: Add retry wrapper and custom exception in google_sheets_service.py | AR-ARCH-005 | — | done | 2026-08-11T20:30 |
| T-39 | Storage: Consolidate _write_specialist_fields() to single batchUpdate | AR-ARCH-005 | T-38 | done | 2026-08-11T20:32 |
| T-40 | Storage: Consolidate _add_formulas_for_row() to single batchUpdate | AR-ARCH-005 | T-38 | done | 2026-08-11T20:33 |
| T-41 | Storage: Consolidate _apply_updates() loop to single batchUpdate | AR-ARCH-005 | T-38 | done | 2026-08-11T20:34 |
| T-42 | Service: Add inter-specialist throttle delay in sync loop | AR-ARCH-005 | T-38 | done | 2026-08-11T20:35 |
| T-43 | Audit: Full repo audit — zero ERR/WARN in touched files | AR-ARCH-005 | T-42 | done | 2026-08-11T20:36 |
