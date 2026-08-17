# Tasks: WF-1 v3 — Invalid Rate Handling

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Model: change Specialist rates to `Decimal \| None = None` | FR-SYNC-001, FR-SYNC-RATES-001 | — | done | 2026-08-17T17:50 |
| T-02 | Storage: `_parse_decimal()` returns `None` for empty/invalid | FR-SYNC-001, FR-SYNC-RATES-001 | T-01 | done | 2026-08-17T17:51 |
| T-03 | Storage: `_write_specialist_fields()` guards against `None` rates | FR-SYNC-001, FR-SYNC-RATES-001 | T-01 | done | 2026-08-17T17:52 |
| T-04 | Service: `sync_project_rates()` validates rates, logs ERROR, skips invalid | FR-SYNC-001, FR-SYNC-RATES-001 | T-01, T-02 | done | 2026-08-17T17:53 |
| T-05 | Storage: `archive_current_period()` guards against `None` rates | FR-SYNC-001 | T-01 | done | 2026-08-17T17:54 |
| T-06 | Tests: `_parse_decimal()` unit tests | FR-SYNC-001, FR-SYNC-RATES-001 | T-02 | done | 2026-08-17T17:55 |
| T-07 | Tests: `sync_project_rates()` invalid rate handling tests | FR-SYNC-001, FR-SYNC-RATES-001 | T-04 | done | 2026-08-17T17:56 |
| T-08 | Audit: full repo audit — zero ERR, zero WARN in touched files | FR-SYNC-001, FR-SYNC-RATES-001 | T-01–T-07 | done | 2026-08-17T17:57 |
