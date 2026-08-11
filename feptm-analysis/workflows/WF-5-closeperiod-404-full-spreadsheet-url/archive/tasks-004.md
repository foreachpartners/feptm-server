# Tasks: Write numbers, not strings, to Current Period and Archive

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-56 | Storage: _write_specialist_fields — numberValue for rates, stringValue for name/role | FR-SPECIALIST-001 | — | done | 2026-08-12T00:17 |
| T-57 | Storage: archive_current_period — drop str() on per-specialist row values | FR-PAYMENT-001 | — | done | 2026-08-12T00:17 |
| T-58 | Storage: archive_current_period — drop str() on summary row values | FR-PAYMENT-001 | — | done | 2026-08-12T00:17 |
| T-59 | Audit: Full repo audit — zero ERR/WARN in touched files | FR-PAYMENT-001, FR-SPECIALIST-001 | T-58 | done | 2026-08-12T00:17 |
