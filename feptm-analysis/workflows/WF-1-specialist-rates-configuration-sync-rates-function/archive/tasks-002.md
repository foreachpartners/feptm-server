# Tasks: FR-SYNC-RATES-001 (fix)

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-F1 | Storage: Add `_find_specialist_row` helper + `sync_rates_to_current_period` to `project_storage.py` | FR-SYNC-RATES-001 | — | done | 2026-08-08T22:39 |
| T-F2 | Protocols: Add `sync_rates_to_current_period` to `ProjectStorageProtocol` | FR-SYNC-RATES-001 | T-F1 | done | 2026-08-08T22:39 |
| T-F3 | Service: Replace `update_current_period` with `sync_rates_to_current_period` in `sync_project_rates` | FR-SYNC-RATES-001 | T-F2 | done | 2026-08-08T22:39 |
| T-F4 | Tests: Update mock method names in `test_project_service.py` | FR-SYNC-RATES-001 | T-F3 | done | 2026-08-08T22:40 |
| T-F5 | Audit: Typecheck + tests + zero ERR/WARN in touched files | FR-SYNC-RATES-001 | T-F4 | done | 2026-08-08T22:40 |
