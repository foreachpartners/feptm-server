# Tasks: FR-SYNC-001, FR-SYNC-RATES-001, AR-DATA-001

| # | Task | Req | Depends on | Status | Completed |
|---|------|-----|------------|--------|-----------|
| T-01 | Model: Add `row_index` and `display_name` fields to Specialist model | AR-DATA-001 | — | done | 2026-08-09T21:01 |
| T-02 | Storage: Populate `row_index` in `_parse_row`; use `row_index` in `_prepare_updates` for precise row targeting | AR-DATA-001 | T-01 | done | 2026-08-09T21:03 |
| T-03 | Storage: Use `display_name` in `add_specialist_to_report`, `update_current_period`, `sync_rates_to_current_period`, `_write_specialist_fields` | AR-DATA-001 | T-01 | done | 2026-08-09T21:05 |
| T-04 | Service: Add `_resolve_display_names` helper; call in `sync_project_specialists` and `sync_project_rates` | FR-SYNC-001, FR-SYNC-RATES-001 | T-01 | done | 2026-08-09T21:07 |
| T-05 | GoogleSheetsService: Add `AR-DATA-001:allow` to `find_specialist_row_index` | AR-DATA-001 | — | done | 2026-08-09T21:08 |
| T-06 | Tests: `test_parse_rows_sets_row_index`, `test_prepare_updates_uses_row_index` | AR-DATA-001 | T-02 | done | 2026-08-09T21:19 |
| T-07 | Tests: Display name resolution, duplicate name write-back, disambiguated tabs | FR-SYNC-001, FR-SYNC-RATES-001 | T-03, T-04 | done | 2026-08-09T21:19 |
| T-08 | Audit: Full repo audit — zero ERR, zero WARN in touched files | FR-SYNC-001, FR-SYNC-RATES-001, AR-DATA-001 | T-01..T-07 | done | 2026-08-09T21:20 |
